#!/usr/bin/env python3
"""Read-only, value-free inventory of approved live Bob systemd directive names.

Reads unit content only when its SHA256 matches the existing PRIVATE topology
report. Never stores or prints any unit directive VALUES, unknown key names,
commands, environment, credentials, paths, or original unit bodies.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import sys

from inventory_service_topology import EXPECTED_NAMES
from prepare_service_template_candidates import exact_read, select_roots
from report_service_readiness import read_private_report

ALLOWED_SECTIONS = {"Unit", "Service", "Timer", "Install"}
# Fixed known systemd keys; unknown/custom keys are counted but NEVER echoed.
# This is a shape audit, not a replacement for review of actual values.
KNOWN_KEYS = {
    "After", "Before", "Wants", "Requires", "Requisite", "BindsTo",
    "PartOf", "Conflicts", "OnFailure", "OnSuccess", "Description",
    "Documentation", "ConditionPathExists", "AssertPathExists",
    "ConditionUser", "ConditionVirtualization", "StartLimitIntervalSec",
    "StartLimitBurst", "StopWhenUnneeded", "RefuseManualStart",
    "RequiresMountsFor", "DefaultDependencies",
    "Type", "ExecStart", "ExecStartPre", "ExecStartPost", "ExecStop",
    "ExecStopPost", "ExecReload", "WorkingDirectory", "User", "Group",
    "SupplementaryGroups", "Environment", "EnvironmentFile", "PassEnvironment",
    "UnsetEnvironment", "LoadCredential", "LoadCredentialEncrypted",
    "SetCredential", "SetCredentialEncrypted", "Restart", "RestartSec",
    "RestartPreventExitStatus", "RestartForceExitStatus", "SuccessExitStatus",
    "TimeoutStartSec", "TimeoutStopSec", "TimeoutSec", "RuntimeMaxSec",
    "KillMode", "KillSignal", "SendSIGKILL", "RemainAfterExit",
    "PIDFile", "GuessMainPID", "NotifyAccess", "WatchdogSec",
    "StandardOutput", "StandardError", "SyslogIdentifier", "LogLevelMax",
    "NoNewPrivileges", "PrivateTmp", "PrivateDevices", "ProtectSystem",
    "ProtectHome", "ProtectKernelTunables", "ProtectKernelModules",
    "ProtectControlGroups", "ProtectClock", "ProtectHostname",
    "ReadWritePaths", "ReadOnlyPaths", "InaccessiblePaths",
    "RestrictAddressFamilies", "RestrictNamespaces", "RestrictSUIDSGID",
    "SystemCallFilter", "SystemCallErrorNumber", "CapabilityBoundingSet",
    "AmbientCapabilities", "MemoryDenyWriteExecute", "LockPersonality",
    "UMask", "LimitNOFILE", "LimitNPROC", "TasksMax", "MemoryMax",
    "MemoryHigh", "CPUQuota", "Delegate", "Slice", "RootDirectory",
    "RootImage", "DynamicUser", "StateDirectory", "CacheDirectory",
    "RuntimeDirectory", "LogsDirectory", "ConfigurationDirectory",
    "IPAddressDeny", "IPAddressAllow", "ProtectProc", "ProcSubset",
    "OnBootSec", "OnStartupSec", "OnUnitActiveSec", "OnUnitInactiveSec",
    "OnCalendar", "AccuracySec", "RandomizedDelaySec", "Persistent",
    "WakeSystem", "FixedRandomDelay", "Unit",
    "WantedBy", "RequiredBy", "Also", "Alias", "DefaultInstance",
}
DIRECTIVE_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,79}$")
MAX_RECORDS = 120


def unknown_family(key: str) -> str:
    """Return only one of a few fixed category words, never an unknown name."""
    if not DIRECTIVE_KEY.fullmatch(key):
        return "other"
    groups = (
        ("Exec", "execution"),
        ("Restart", "restart"),
        ("StartLimit", "start-rate"),
        ("Timeout", "timeout"),
        ("Kill", "shutdown"),
        ("Environment", "environment"),
        ("LoadCredential", "credentials"),
        ("SetCredential", "credentials"),
        ("Protect", "security"),
        ("Private", "security"),
        ("Restrict", "security"),
        ("SystemCall", "security"),
        ("Condition", "conditions"),
        ("Assert", "conditions"),
        ("Limit", "resource-limits"),
        ("Memory", "resource-limits"),
        ("CPU", "resource-limits"),
        ("Watchdog", "health"),
        ("Notify", "health"),
        ("Log", "logging"),
        ("Standard", "logging"),
    )
    for prefix, family in groups:
        if key.startswith(prefix):
            return family
    return "other"


def describe(data: bytes) -> dict:
    """Analyze raw bytes internally; serialize only allowlisted key NAMES."""
    text = data.decode("utf-8")
    section = ""
    continuation = False
    known: dict[str, Counter[str]] = {}
    unknown_count: Counter[str] = Counter()
    unknown_groups: dict[str, Counter[str]] = {}
    unknown_sections = 0
    for line in text.splitlines():
        if len(line) > 4096:
            raise ValueError("Oversized directive line")
        stripped = line.strip()
        if continuation:
            continuation = stripped.endswith("\\")
            continue
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
            if section not in ALLOWED_SECTIONS:
                unknown_sections += 1
            continue
        key, sep, value = stripped.partition("=")
        key = key.strip()
        if not sep:
            unknown_count["other"] += 1
            continue
        # Explicit continuation handling prevents leaking data masquerading as
        # a separately typed directive.
        continuation = value.rstrip().endswith("\\")
        if section in ALLOWED_SECTIONS and DIRECTIVE_KEY.fullmatch(key):
            if key in KNOWN_KEYS:
                known.setdefault(section, Counter())[key] += 1
            else:
                unknown_count[section] += 1
                unknown_groups.setdefault(section, Counter())[unknown_family(key)] += 1
        else:
            unknown_count["other"] += 1
    return {
        "known_directive_names_by_section": {
            section: dict(sorted(counts.items()))
            for section, counts in sorted(known.items())
        },
        "unrecognized_directive_counts_by_section": dict(sorted(unknown_count.items())),
        "unrecognized_directive_families_by_section": {
            section: dict(sorted(counts.items()))
            for section, counts in sorted(unknown_groups.items())
        },
        "unrecognized_section_count": unknown_sections,
    }


def inspect(report: dict, roots: dict[str, list[Path]]) -> dict:
    records = report.get("unit_files")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_RECORDS:
        raise ValueError("Invalid topology records")
    output = []
    for index, record in enumerate(records, 1):
        if (not isinstance(record, dict) or record.get("unit") not in EXPECTED_NAMES
                or record.get("scope") not in {"user", "system"}
                or record.get("kind") not in {"unit", "dropin"}):
            raise ValueError("Unexpected unit record")
        data = exact_read(record, roots)
        output.append({
            "index": index,
            "scope": record["scope"], "unit": record["unit"],
            "kind": record["kind"], "shape": describe(data),
        })
    return {
        "report_version": 1,
        "purpose": "PRIVATE value-free systemd directive-name audit; not deployable",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files_checked": len(output),
        "unit_files": output,
        "note": "Only fixed known directive names and counts, never values or unknown names",
    }


def save_private(report: dict, directory: Path) -> Path:
    if directory.is_symlink():
        raise PermissionError("Symlink output directory refused")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (not directory.is_dir()
            or stat.S_IMODE(directory.stat().st_mode) & 0o077):
        raise PermissionError("Output directory is not private")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = directory / ("bob-directive-names-" + stamp + ".json")
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topology-report", required=True, type=Path)
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Refusing root user")
    try:
        topology = read_private_report(args.topology_report)
        audit = inspect(topology, select_roots(Path.home()))
        path = save_private(audit, Path.home() / ".local/state/bob-baseline/directive-audit")
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        print("DIRECTIVE-NAME AUDIT REFUSED:", type(exc).__name__,
              "(no source or services changed)", file=sys.stderr)
        return 1
    print("PRIVATE DIRECTIVE-NAME AUDIT: PASS")
    print("SHA-verified source files:", audit["files_checked"])
    print("Private audit report:", path)
    for record in audit["unit_files"]:
        if record["unit"] == "openclaw-gateway.service":
            shape = record["shape"]
            for section, keys in shape["known_directive_names_by_section"].items():
                print("  Gateway", record["kind"], record["scope"], section,
                      "known keys:", ", ".join(sorted(keys)))
            print("  Gateway unrecognized directive count:",
                  sum(shape["unrecognized_directive_counts_by_section"].values()))
            for section, families in shape["unrecognized_directive_families_by_section"].items():
                print("  Gateway unrecognized", section, "family categories:",
                      ", ".join(f"{group}={count}" for group, count in sorted(families.items())))
    print("No directive values, unknown key names, credentials or paths printed.")
    print("No units, timers, processes, Windows startup or database changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
