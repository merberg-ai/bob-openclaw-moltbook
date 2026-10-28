#!/usr/bin/env python3
"""Read-only readiness check for the actual Bob user/system systemd units.

Input is the existing private topology JSON. Output is allowlisted unit names,
systemctl state categories, and a user-linger flag. No raw unit text, command
lines, environment variables, secrets or installed files are modified.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from inventory_service_topology import EXPECTED_NAMES

MAX_REPORT_BYTES = 2 * 1024 * 1024
SAFE_ACTIVE = {"active", "inactive", "activating", "deactivating", "failed", "reloading", "maintenance"}
SAFE_LOAD = {"loaded", "not-found", "masked", "error", "bad-setting", "stub", "merged"}
SAFE_ENABLE = {"enabled", "enabled-runtime", "disabled", "static", "indirect", "masked", "masked-runtime",
               "linked", "linked-runtime", "alias", "generated", "transient", "bad", "preset"}
SAFE_SUB = {"running", "dead", "waiting", "exited", "failed", "start", "stop", "auto-restart", "listening"}
UNITS = set(EXPECTED_NAMES)


def classification(value: str | None, allowed: set[str]) -> str:
    return value if value in allowed else "unknown"


def read_private_report(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("Refusing symlink report")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as fh:
        info = os.fstat(fh.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_REPORT_BYTES:
            raise ValueError("Invalid report file type or size")
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError("Private report permissions or owner are unsafe")
        data = fh.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("Report too large")
    report = json.loads(data)
    if not isinstance(report, dict) or report.get("report_version") != 1:
        raise ValueError("Unexpected report format")
    if report.get("purpose") != "private read-only Bob service topology; not a deployable unit template":
        raise ValueError("Not a service topology report")
    if not isinstance(report.get("unit_files"), list):
        raise ValueError("Missing unit records")
    return report


def discover_recent_report(directory: Path) -> Path:
    if directory.is_symlink():
        raise ValueError("Private baseline directory is a symlink")
    # A report has an intentionally generic inventory- name shared by multiple tools.
    # Parse the newest one with the matching topology purpose rather than guessing.
    for path in sorted(directory.glob("inventory-*.json"), reverse=True)[:60]:
        try:
            report = read_private_report(path)
            if isinstance(report.get("unit_files"), list):
                return path
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    raise FileNotFoundError("No private service-topology report found")


def unit_pairs(report: dict) -> list[tuple[str, str]]:
    pairs = set()
    for item in report["unit_files"]:
        if not isinstance(item, dict):
            continue
        name, scope = item.get("unit"), item.get("scope")
        if name in UNITS and scope in {"user", "system"}:
            pairs.add((scope, name))
    return sorted(pairs)


def systemd_status(scope: str, name: str) -> dict:
    if scope not in {"user", "system"} or name not in UNITS:
        raise ValueError("Unit outside trusted inventory")
    try:
        result = subprocess.run(
            ["systemctl", "--user" if scope == "user" else "--system",
             "show", name, "--no-pager",
             "--property=LoadState,ActiveState,SubState,UnitFileState"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=4, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"load": "unavailable", "active": "unavailable", "sub": "unavailable", "enabled": "unavailable"}
    if result.returncode != 0:
        return {"load": "unavailable", "active": "unavailable", "sub": "unavailable", "enabled": "unavailable"}
    props = {}
    for row in result.stdout.splitlines():
        key, sep, val = row.partition("=")
        if sep and key in {"LoadState", "ActiveState", "SubState", "UnitFileState"}:
            props[key] = val.strip()
    return {
        "load": classification(props.get("LoadState"), SAFE_LOAD),
        "active": classification(props.get("ActiveState"), SAFE_ACTIVE),
        "sub": classification(props.get("SubState"), SAFE_SUB),
        "enabled": classification(props.get("UnitFileState"), SAFE_ENABLE),
    }


def linger_status() -> str:
    try:
        import pwd
        username = pwd.getpwuid(os.geteuid()).pw_name
        run = subprocess.run(
            ["loginctl", "show-user", username, "--property=Linger", "--no-pager"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=4, check=False,
        )
        if run.returncode == 0 and run.stdout.strip() in {"Linger=yes", "Linger=no"}:
            return run.stdout.strip().split("=")[1]
    except (OSError, KeyError, subprocess.TimeoutExpired):
        pass
    return "unavailable"


def summarize(report: dict, get_status=systemd_status) -> list[dict]:
    return [{"scope": scope, "unit": name, **get_status(scope, name)}
            for scope, name in unit_pairs(report)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Private report from inventory_service_topology.py")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as openclaw user, not root")
    try:
        path = args.report or discover_recent_report(
            Path.home() / ".local/state/bob-baseline"
        )
        rows = summarize(read_private_report(path))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("READINESS CHECK REFUSED:", type(exc).__name__,
              "(no live services changed)", file=sys.stderr)
        return 1
    print("Bob service readiness (read-only; values are allowlisted):")
    for row in rows:
        print(" ", row["scope"], row["unit"],
              "load=" + row["load"], "active=" + row["active"],
              "sub=" + row["sub"], "enabled=" + row["enabled"])
    if not rows:
        print("  No allowlisted units found in private topology report.")
    for name in ("bob-moltbook-scout.service", "bob-moltbook-scout.timer"):
        both = [row for row in rows if row["unit"] == name]
        print("Duplicate-scope", name, "user/system=" + (
            "both present" if len(both) == 2 else "not both found"))
    print("OpenClawLab Linux user linger:", linger_status())
    print("An enabled user unit does not itself launch WSL or Windows at boot.")
    print("No units, timers, Windows startup settings or credentials were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
