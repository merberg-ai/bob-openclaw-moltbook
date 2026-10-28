#!/usr/bin/env python3
"""Classify the live Activity Manager service entrypoint without printing its contents.

Read only. No changes to systemd, launchers, executable files or databases.
This is evidence for designing a future installer, not deployment approval.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

UNIT = "bob-activity-manager.service"
MANAGER = Path.home() / ".local/bin/bob-activity-manager"
KEYS = ("LoadState", "ActiveState", "SubState", "FragmentPath", "DropInPaths", "ExecStart")


def classify(values: dict[str, str], manager: Path) -> dict[str, bool]:
    entry = values.get("ExecStart", "")
    # A definite direct reference is preferable to guessing from wrappers.
    # Token boundaries prevent sibling filenames such as manager-old matching.
    boundary = r"(?<![A-Za-z0-9_./-])" + re.escape(str(manager)) + r"(?![A-Za-z0-9_./-])"
    return {
        "service_loaded": values.get("LoadState") == "loaded",
        "service_running": values.get("ActiveState") == "active" and values.get("SubState") == "running",
        "direct_manager_reference": bool(re.search(boundary, entry)),
        "unit_fragment_declared": bool(values.get("FragmentPath")),
        "has_dropins": bool(values.get("DropInPaths", "").strip()),
        "service_launch_details_ambiguous": not bool(re.search(boundary, entry)),
    }


def inspect() -> dict[str, bool]:
    env = {"PATH": "/usr/bin:/bin", "LANG": "C"}
    for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
        if key in os.environ:
            env[key] = os.environ[key]
    result = subprocess.run(
        ["systemctl", "--user", "show", UNIT,
         "--property=" + ",".join(KEYS), "--no-pager"],
        check=False, capture_output=True, text=True, timeout=8, env=env,
    )
    if result.returncode:
        raise ValueError("systemctl report unavailable")
    values = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            raise ValueError("unexpected systemctl output")
        key, value = line.split("=", 1)
        if key not in KEYS or key in values:
            raise ValueError("unexpected systemctl property")
        values[key] = value
    if set(values) != set(KEYS):
        raise ValueError("incomplete systemctl report")
    return classify(values, MANAGER)


def main() -> int:
    try:
        status = inspect()
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print("SERVICE ENTRYPOINT CLASSIFICATION: REFUSED")
        print("No service state or private launch parameters changed.")
        return 1
    for key, value in status.items():
        print(key + ":", "YES" if value else "NO")
    print("No unit files, launch arguments, environment values, or paths printed.")
    print("No changes to live Bob. This classification is NOT deployment approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
