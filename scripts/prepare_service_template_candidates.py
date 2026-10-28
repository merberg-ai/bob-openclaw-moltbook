#!/usr/bin/env python3
"""Prepare NON-DEPLOYABLE, sanitized systemd template candidates from live units.

Read-only against installed units. The only writes are mode-0600, private
template-review artifacts outside Git. Never publishes unit bodies, paths,
Exec* arguments, Environment values or arbitrary user-supplied strings.

This is a *review input*, NOT a service installer or faithful unit recreation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

from report_service_readiness import read_private_report
from inventory_service_topology import EXPECTED_NAMES, read_unit

MAX_UNIT_COUNT = 120
ALLOWED_SCOPES = {"user", "system"}
ALLOWED_KINDS = {"unit", "dropin"}
ALLOWED_SECTIONS = {"Unit", "Service", "Timer", "Install"}
DEPENDENCIES = {
    "basic.target", "default.target", "network.target", "network-online.target",
    "multi-user.target", "timers.target", "sysinit.target",
} | EXPECTED_NAMES
DEPENDENCY_KEYS = {"After", "Before", "Wants", "Requires", "WantedBy", "PartOf", "BindsTo"}
SERVICE_TYPES = {"simple", "exec", "oneshot", "notify", "forking", "idle", "dbus"}
RESTART_TYPES = {"no", "always", "on-failure", "on-abnormal", "on-abort", "on-watchdog", "on-success"}
BOOL_VALUES = {"yes", "no", "true", "false"}
BOOL_KEYS = {
    "Persistent", "RemainAfterExit", "NoNewPrivileges", "PrivateTmp",
    "ProtectHome", "ProtectKernelTunables", "ProtectControlGroups",
    "MemoryDenyWriteExecute",
}
SAFE_TIMER_KEYS = {
    "OnCalendar", "OnBootSec", "OnStartupSec", "OnUnitActiveSec",
    "OnUnitInactiveSec", "AccuracySec", "RandomizedDelaySec",
}
DURATION_KEYS = SAFE_TIMER_KEYS - {"OnCalendar"}
# No slash, backslash, quote, dollar sign, control character, equals or
# shell metacharacter can survive into a timing field.
CALENDAR_RE = re.compile(r"^(?=.{1,96}$)[A-Za-z0-9*.,: +~!-]*(?:[0-9]/[0-9]+[A-Za-z0-9*.,: +~!-]*)*$")
DURATION_RE = re.compile(r"^[0-9]{1,7}(?:us|ms|s|sec|seconds?|min|minutes?|h|hours?|d|days?|w|weeks?)?$")
SENSITIVE_KEYS = {
    "ExecStart", "ExecStartPre", "ExecStartPost", "ExecStop", "ExecReload",
    "Environment", "EnvironmentFile", "PassEnvironment",
    "LoadCredential", "LoadCredentialEncrypted", "SetCredential",
    "SetCredentialEncrypted", "WorkingDirectory", "User", "Group",
    "SupplementaryGroups", "ReadWritePaths", "ReadOnlyPaths",
    "InaccessiblePaths", "RootDirectory", "RootImage", "Description",
    "Documentation", "ConditionPathExists", "AssertPathExists",
}
SAFE_PASSTHROUGH = {"Type", "Restart", "ProtectSystem", "Unit"}
MAX_LINE = 4096


def select_roots(home: Path) -> dict[str, list[Path]]:
    return {
        "user": [home / ".config/systemd/user", Path("/usr/lib/systemd/user")],
        "system": [Path("/etc/systemd/system"), Path("/lib/systemd/system")],
    }


def candidate_path(root: Path, record: dict) -> Path:
    if record["kind"] == "unit":
        return root / record["unit"]
    filename = record.get("filename")
    if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}\.conf", filename):
        raise ValueError("Unexpected drop-in filename")
    return root / (record["unit"] + ".d") / filename


def exact_read(record: dict, roots: dict[str, list[Path]]) -> bytes:
    sha = record.get("sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("Missing SHA-256 fingerprint")
    matches = []
    for root in roots[record["scope"]]:
        if root.is_symlink() or not root.is_dir():
            continue
        file = candidate_path(root, record)
        if file.is_symlink():
            raise ValueError("Symlink unit source refused")
        if file.parent.is_symlink():
            raise ValueError("Symlink unit directory refused")
        if not file.is_file():
            continue
        data = read_unit(file)  # O_NOFOLLOW, regular file and size-limited
        if hashlib.sha256(data).hexdigest() == sha:
            matches.append(data)
        else:
            raise ValueError("Installed unit changed since inventory")
    if len(matches) != 1:
        raise ValueError("Expected one exact matching source unit")
    return matches[0]


def sanitized_shape(data: bytes) -> dict:
    text = data.decode("utf-8")
    safe: dict[str, dict[str, list[str]]] = {}
    hidden: dict[str, int] = {}
    section = None
    continued = False
    dropped = 0
    for line in text.splitlines():
        if len(line) > MAX_LINE:
            raise ValueError("Unexpectedly long unit line")
        raw = line.strip()
        if continued:
            continued = raw.endswith("\\")
            dropped += 1
            continue
        if not raw or raw.startswith(("#", ";")):
            continue
        if raw.startswith("[") and raw.endswith("]"):
            section = raw[1:-1] if raw[1:-1] in ALLOWED_SECTIONS else None
            continue
        if section is None:
            dropped += 1
            continue
        key, sep, value = raw.partition("=")
        key = key.strip()
        value = value.strip()
        # Do not allow unexamined multiline values to be copied.
        if value.endswith("\\"):
            continued = True
            dropped += 1
            continue
        if not sep or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,79}", key):
            dropped += 1
            continue
        emit = None
        if key in DEPENDENCY_KEYS:
            values = value.split()
            if values and len(values) <= 20 and all(v in DEPENDENCIES for v in values):
                emit = " ".join(values)
        elif section == "Timer" and key in SAFE_TIMER_KEYS:
            if key == "OnCalendar" and CALENDAR_RE.fullmatch(value):
                emit = value
            elif key in DURATION_KEYS and DURATION_RE.fullmatch(value):
                emit = value
        elif key in BOOL_KEYS and value.lower() in BOOL_VALUES:
            emit = value.lower()
        elif section == "Service" and key == "Type" and value in SERVICE_TYPES:
            emit = value
        elif section == "Service" and key == "Restart" and value in RESTART_TYPES:
            emit = value
        elif section == "Service" and key == "RestartSec" and DURATION_RE.fullmatch(value):
            emit = value
        elif section == "Service" and key == "ProtectSystem" and value in {"yes", "no", "full", "strict"}:
            emit = value
        elif section == "Timer" and key == "Unit" and value in EXPECTED_NAMES:
            emit = value
        if emit is not None:
            safe.setdefault(section, {}).setdefault(key, []).append(emit)
        elif key in SENSITIVE_KEYS or key in DEPENDENCY_KEYS or key in SAFE_TIMER_KEYS or key in BOOL_KEYS or key in SAFE_PASSTHROUGH or key == "RestartSec":
            hidden[key] = hidden.get(key, 0) + 1
        else:
            dropped += 1
    return {
        "safe": safe,
        "withheld_known_keys": dict(sorted(hidden.items())),
        "unclassified_directives_count": dropped,
    }


def make_template(unit: str, scope: str, kind: str, shape: dict) -> str:
    lines = [
        "# NOT DEPLOYABLE - REVIEW CANDIDATE ONLY",
        "# Original Exec*, Environment*, paths and credentials were NOT copied.",
        "# Generated from hash-verified installed configuration.",
        "# To become deployable: reconstruct and independently review exact behavior.",
        "# Scope: " + scope,
        "# Unit: " + unit,
        "# Kind: " + kind,
    ]
    for section in ("Unit", "Service", "Timer", "Install"):
        values = shape["safe"].get(section, {})
        if not values and section not in {"Service", "Timer"}:
            continue
        if section == "Service" and not unit.endswith(".service"):
            continue
        if section == "Timer" and not unit.endswith(".timer"):
            continue
        lines.extend(["", "[" + section + "]"])
        for key in sorted(values):
            for value in values[key]:
                lines.append(key + "=" + value)
        if section == "Service":
            lines.append("ExecStart=@REVIEW_REQUIRED_NOT_DEPLOYABLE@")
    lines.extend(["", "# WITHHELD KNOWN DIRECTIVES (key names only):"])
    for key, count in shape["withheld_known_keys"].items():
        lines.append("# " + key + ": " + str(count))
    lines.append("# OTHER UNCLASSIFIED DIRECTIVES: " + str(shape["unclassified_directives_count"]))
    return "\n".join(lines) + "\n"


def prepare(report: dict, roots: dict[str, list[Path]]) -> tuple[dict, dict[str, str]]:
    records = report["unit_files"]
    if not 1 <= len(records) <= MAX_UNIT_COUNT:
        raise ValueError("Invalid unit record count")
    outputs = {}
    summaries = []
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError("Invalid unit record")
        if record.get("unit") not in EXPECTED_NAMES:
            raise ValueError("Unexpected unit name")
        if record.get("scope") not in ALLOWED_SCOPES or record.get("kind") not in ALLOWED_KINDS:
            raise ValueError("Unexpected scope/kind")
        name = f"{index:03d}-{record['scope']}-{record['unit']}-{record['kind']}.template.txt"
        contents = exact_read(record, roots)
        shape = sanitized_shape(contents)
        template = make_template(record["unit"], record["scope"], record["kind"], shape)
        outputs["candidates/" + name] = template
        summaries.append({
            "scope": record["scope"],
            "unit": record["unit"],
            "kind": record["kind"],
            "template": name,
            "raw_unit_sha256": hashlib.sha256(contents).hexdigest(),
            "safe_directive_keys": sorted({k for group in shape["safe"].values() for k in group}),
            "withheld_known_keys": shape["withheld_known_keys"],
            "unclassified_directives_count": shape["unclassified_directives_count"],
        })
    return {
        "format": "bob-v070-sanitized-service-review",
        "version": 1,
        "deployable": False,
        "source_count": len(summaries),
        "unit_templates": summaries,
        "warnings": [
            "NOT DEPLOYABLE; must be manually reviewed and reconstructed",
            "All Exec and Environment values omitted; no original unit bodies included",
            "Keep output private until every member is reviewed before sharing",
        ],
    }, outputs


def private_output(folder: Path, manifest: dict, outputs: dict[str, str]) -> Path:
    if folder.is_symlink():
        raise PermissionError("Private output folder cannot be symlinked")
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not folder.is_dir() or stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise PermissionError("Private output folder requires 0700")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = folder / ("bob-service-candidates-" + stamp + ".zip")
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as zipout:
                zipout.writestr("REVIEW-ONLY-MANIFEST.json",
                                json.dumps(manifest, indent=2, sort_keys=True))
                for name, data in sorted(outputs.items()):
                    zipout.writestr(name, data)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topology-report", required=True, type=Path)
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as unprivileged OpenClawLab operator")
    try:
        report = read_private_report(args.topology_report)
        manifest, templates = prepare(report, select_roots(Path.home()))
        out = private_output(Path.home() / ".local/state/bob-baseline/service-reviews",
                             manifest, templates)
    except (OSError, ValueError, RuntimeError, UnicodeError, KeyError, TypeError,
            json.JSONDecodeError) as exc:
        print("SERVICE TEMPLATE REVIEW REFUSED:", type(exc).__name__,
              "(no services or live configuration changed)", file=sys.stderr)
        return 1
    print("Private sanitized template candidate archive:", out)
    print("Validated units/drop-ins:", manifest["source_count"])
    print("Deployable: NO")
    print("Only allowlisted static unit/timer directives are included.")
    print("Exec, Environment and path values withheld; raw unit contents excluded.")
    print("Manual review required BEFORE sharing candidate archive.")
    print("Live services, unit files, state, Windows startup and credentials untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
