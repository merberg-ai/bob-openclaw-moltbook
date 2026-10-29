#!/usr/bin/env python3
"""Read-only systemd service topology review for the installed Bob/OpenClaw host.

Reads only known Bob/OpenClaw unit files and drop-ins. Report never contains
Environment= values, Exec*= arguments, raw unit bodies, usernames, tokens,
or other arbitrary property values. Nothing is started, stopped or installed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from inventory_live_host import (
    file_fingerprint, inventory_unit_states, inventory_units,
    is_unit_candidate, write_private_report,
)

MAX_UNIT_BYTES = 256 * 1024
MAX_FILES = 120
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,79}$")
DEP_NAME = re.compile(r"^(?:(?:bob|openclaw)-[a-zA-Z0-9@_.-]{1,96}\.(?:service|timer|target)|(?:basic|default|network|network-online|multi-user|timers|sysinit)\.target)$")
BOB_NAME = re.compile(r"(?<![A-Za-z0-9_-])(?:bob-activity-manager|bob-lan-config|bob-moltbook-publisher|bob-moltbook-scout|bob-original-worker|bobctl|openclaw-gateway)(?![A-Za-z0-9_-])")
EXEC_KEYS = {"ExecStart", "ExecStartPre", "ExecStartPost", "ExecStop", "ExecReload"}
DEPENDENCY_KEYS = {"After", "Before", "Requires", "Wants", "WantedBy", "PartOf", "BindsTo"}
TIMER_KEYS = {"OnCalendar", "OnBootSec", "OnUnitActiveSec", "OnUnitInactiveSec", "OnStartupSec", "Persistent", "RandomizedDelaySec", "AccuracySec"}
SECURITY_KEYS = {"NoNewPrivileges", "PrivateTmp", "ProtectSystem", "ProtectHome", "ProtectKernelTunables", "ProtectControlGroups", "RestrictAddressFamilies", "ReadWritePaths", "InaccessiblePaths", "MemoryDenyWriteExecute", "CapabilityBoundingSet"}
SAFE_TYPES = {"simple", "exec", "oneshot", "notify", "forking", "idle", "dbus"}
SAFE_RESTART = {"no", "always", "on-failure", "on-abnormal", "on-abort", "on-watchdog", "on-success"}
EXPECTED_NAMES = {
    "bob-activity-manager.service", "bob-moltbook-publisher.service",
    "bob-moltbook-publisher.timer", "bob-moltbook-scout.service",
    "bob-moltbook-scout.timer", "bob-original-worker.service",
    "bob-original-worker.timer", "bob-startup-reconcile.service",
    "bob-startup-reconcile.timer", "openclaw-gateway.service",
}


def unit_name_from_path(path: Path) -> str | None:
    parent = path.parent.name
    if parent.endswith((".service.d", ".timer.d")):
        name = parent[:-2]
    else:
        name = path.name
    return name if is_unit_candidate(name) else None


def read_unit(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError("Refusing symlink unit")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as f:
        info = os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_UNIT_BYTES:
            raise ValueError("Unit is not a regular small file")
        data = f.read(MAX_UNIT_BYTES + 1)
        if len(data) > MAX_UNIT_BYTES or b"\0" in data:
            raise ValueError("Unit is too large or binary")
        return data


def safe_directives(text: str) -> dict:
    counts: Counter[str] = Counter()
    deps: set[str] = set()
    referenced: set[str] = set()
    unsafe_directives = set()
    config: dict[str, str] = {}
    sections: set[str] = set()
    for line in text.splitlines():
        if not line or line.lstrip().startswith(("#", ";")):
            continue
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
            if section in {"Unit", "Service", "Timer", "Install"}:
                sections.add(section)
            continue
        key, sep, raw = line.partition("=")
        key = key.strip()
        if not sep or not KEY_RE.fullmatch(key):
            continue
        counts[key] += 1
        if key in DEPENDENCY_KEYS:
            for token in raw.split():
                if DEP_NAME.fullmatch(token):
                    deps.add(token)
        elif key in EXEC_KEYS:
            # Record only recognized program names, not paths or command args.
            referenced.update(BOB_NAME.findall(raw))
        elif key in {"Type", "Restart"}:
            value = raw.strip()
            if key == "Type" and value in SAFE_TYPES:
                config["service_type"] = value
            if key == "Restart" and value in SAFE_RESTART:
                config["restart_policy"] = value
        elif key in {"Environment", "EnvironmentFile", "PassEnvironment", "LoadCredential", "SetCredential", "SetCredentialEncrypted"}:
            unsafe_directives.add(key)
    return {
        "sections": sorted(sections),
        "directive_keys": sorted(counts),
        "exec_directives": {k: counts[k] for k in sorted(EXEC_KEYS) if counts[k]},
        "environment_directives": {k: counts[k] for k in sorted(unsafe_directives)},
        "timer_directives": sorted(k for k in TIMER_KEYS if counts[k]),
        "security_directives_present": sorted(k for k in SECURITY_KEYS if counts[k]),
        "related_units": sorted(deps),
        "referenced_bob_commands": sorted(referenced),
        "has_working_directory": bool(counts["WorkingDirectory"]),
        "has_user_setting": bool(counts["User"]),
        **config,
    }


def collect(unit_directories: list[tuple[str, Path]], *, states: bool = True) -> dict:
    records: list[dict] = []
    identities: set[tuple[str, str]] = set()
    all_names: set[tuple[str, str]] = set()
    for scope, folder in unit_directories:
        if folder.is_symlink() or not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            candidates = []
            if is_unit_candidate(path.name):
                candidates = [path]
            elif path.name.endswith((".service.d", ".timer.d")):
                base = path.name[:-2]
                if is_unit_candidate(base) and path.is_dir() and not path.is_symlink():
                    candidates = [p for p in sorted(path.iterdir()) if p.suffix == ".conf"]
            for entry in candidates:
                name = unit_name_from_path(entry)
                if name is None:
                    continue
                if len(records) >= MAX_FILES:
                    raise ValueError("Unexpectedly many service files")
                identity = (scope, str(entry))
                if identity in identities:
                    continue
                identities.add(identity)
                info = file_fingerprint(entry)
                if "sha256" not in info:
                    records.append({"scope": scope, "unit": name, "type": "unreadable_or_symlink"})
                    continue
                data = read_unit(entry)
                parsed = safe_directives(data.decode("utf-8"))
                records.append({
                    "scope": scope,
                    "unit": name,
                    "kind": "dropin" if entry.suffix == ".conf" else "unit",
                    "filename": entry.name,
                    "sha256": info["sha256"],
                    "size_bytes": info["size_bytes"],
                    "file_world_readable": bool(int(info["mode_octal"], 8) & 0o004),
                    "file_group_readable": bool(int(info["mode_octal"], 8) & 0o040),
                    "shape": parsed,
                })
                all_names.add((scope, name))
    service_states = inventory_unit_states(sorted(all_names)) if states else []
    by_unit = {}
    for entry in records:
        key = (entry["scope"], entry["unit"])
        by_unit.setdefault(key, []).append(entry)
    missing = sorted(EXPECTED_NAMES - {name for _, name in all_names})
    duplicates = sorted(name for name in EXPECTED_NAMES
                        if sum(1 for scope, unit in all_names if unit == name) > 1)
    return {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "private read-only Bob service topology; not a deployable unit template",
        "unit_files": records,
        "states": service_states,
        "counts": {"files": len(records), "units": len(all_names),
                   "user_units": sum(scope == "user" for scope, _ in all_names),
                   "system_units": sum(scope == "system" for scope, _ in all_names)},
        "expected_units_not_found": missing,
        "unit_names_in_both_scopes": duplicates,
        "limits": [
            "No systemd unit bodies, command arguments, environment values or secrets captured",
            "Uses allowlisted Bob/OpenClaw unit names, plus known systemd targets",
            "Does not inspect Windows Task Scheduler, Windows startup folders or login triggers",
            "Unit presence and current state alone do not prove reboot recovery",
            "Keep this report private; filenames and service structure reveal host details",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--skip-states", action="store_true")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as unprivileged openclaw user, not root")
    home = Path.home()
    paths = [
        ("user", home / ".config/systemd/user"),
        ("system", Path("/etc/systemd/system")),
        ("user", Path("/usr/lib/systemd/user")),
        ("system", Path("/lib/systemd/system")),
    ]
    try:
        report = collect(paths, states=not args.skip_states)
        output = args.output_dir or home / ".local/state/bob-baseline"
        path = write_private_report(report, output)
    except (OSError, UnicodeError, ValueError) as exc:
        print("Service topology inventory FAILED:", type(exc).__name__,
              "(no service modifications)", file=sys.stderr)
        return 1
    counts = report["counts"]
    print("Private service topology report:", path)
    print("Read-only inventory:", counts["files"], "files across", counts["units"], "units;",
          counts["user_units"], "user and", counts["system_units"], "system units")
    print("Missing expected names:", len(report["expected_units_not_found"]))
    print("Names present in both scopes:", len(report["unit_names_in_both_scopes"]))
    for name in report["unit_names_in_both_scopes"]:
        print("  duplicate-scope:", name)
    print("No secrets, raw ExecStart commands, environment values or unit bodies printed.")
    print("Services and timers were NOT changed. Report must remain private.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
