#!/usr/bin/env python3
"""Read-only, fail-closed unit/drop-in directive inventory (never prints source)."""
from __future__ import annotations
import os
import re
import subprocess

UNIT = "bob-activity-manager.service"
SENSITIVE = ("EnvironmentFile", "ExecStartPre", "ExecStartPost", "ExecCondition")
OTHER = ("Environment", "WorkingDirectory", "ExecStart")
HEAD = re.compile(r"^# /(?:[^\r\n]+)$")
DIRECTIVE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\s*=(.*)$")


def classify(raw: str) -> dict[str, str]:
    if not raw or len(raw) > 512 * 1024 or "\x00" in raw:
        raise ValueError("invalid unit text")
    seen = {k: [] for k in (*SENSITIVE, *OTHER)}
    unit_sections = 0
    in_service = False
    source_blocks = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if HEAD.match(line):
                source_blocks += 1
            continue
        if line.startswith("["):
            if not line.endswith("]"):
                raise ValueError("invalid section")
            in_service = line.lower() == "[service]"
            if in_service:
                unit_sections += 1
            continue
        match = DIRECTIVE.fullmatch(line)
        if not match:
            if in_service:
                raise ValueError("unrecognized service line")
            continue
        key, value = match.groups()
        if in_service and key in seen:
            seen[key].append(value)
    if not source_blocks or not unit_sections:
        raise ValueError("missing unit sources or service section")
    # This identifies presence in concatenated effective configuration sources.
    # A blank assignment resets earlier values. Conservative UNKNOWN for resets
    # and any reference expanded by systemd, rather than asserting absent.
    result = {}
    for key in SENSITIVE:
        values = seen[key]
        if not values:
            result[key] = "NO"
        elif any(not value.strip() for value in values):
            result[key] = "UNKNOWN"
        else:
            result[key] = "YES"
    result["service_sections_seen"] = "YES"
    result["source_blocks_seen"] = "YES"
    result["custom_execstart_declared"] = "YES" if seen["ExecStart"] else "NO"
    result["inline_environment_declared"] = "YES" if seen["Environment"] else "NO"
    result["working_directory_declared"] = "YES" if seen["WorkingDirectory"] else "NO"
    return result


def main() -> int:
    env = {"PATH": "/usr/bin:/bin", "LANG": "C"}
    for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
        if key in os.environ:
            env[key] = os.environ[key]
    try:
        command = subprocess.run(["systemctl", "--user", "cat", UNIT,
                                  "--no-pager"], capture_output=True,
                                 text=True, check=False, timeout=8, env=env)
        if command.returncode:
            raise ValueError("systemctl cat failed")
        result = classify(command.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print("v0.7.1 UNIT DIRECTIVE INVENTORY: REFUSED")
        print("No configuration or services changed.")
        return 1
    for key, value in result.items():
        print(f"{key}: {value}")
    print("v0.7.1 UNIT DIRECTIVE INVENTORY: COMPLETED (read-only)")
    print("Presence is based on unit text, not final systemd expansion.")
    print("No unit contents, paths, credentials or environment values printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
