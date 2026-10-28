#!/usr/bin/env python3
"""Read-only classification of effective user-systemd settings; no private values printed."""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess

UNIT = "bob-activity-manager.service"
PROPS = ("LoadState", "ActiveState", "SubState", "ExecStart", "FragmentPath",
         "DropInPaths", "WorkingDirectory", "EnvironmentFiles", "Environment",
         "RootDirectory", "RootImage", "DynamicUser", "User", "ExecStartPre",
         "ExecStartPost", "ExecCondition")


def classify(props: dict[str, str], manager: Path) -> dict[str, bool]:
    entry = props.get("ExecStart", "")
    direct = bool(re.search(r"(?<![A-Za-z0-9_./-])" + re.escape(str(manager))
                            + r"(?![A-Za-z0-9_./-])", entry))
    return {
        "service_loaded": props.get("LoadState") == "loaded",
        "service_running": props.get("ActiveState") == "active" and props.get("SubState") == "running",
        "direct_manager_reference": direct,
        "dropins_present": bool(props.get("DropInPaths", "").strip()),
        "custom_working_directory": props.get("WorkingDirectory", "") not in ("", "/"),
        "environment_files_declared": bool(props.get("EnvironmentFiles", "").strip()),
        "inline_environment_declared": bool(props.get("Environment", "").strip()),
        "root_directory_or_image_declared": any(bool(props.get(p, "").strip()) for p in ("RootDirectory", "RootImage")),
        "dynamic_user_enabled": props.get("DynamicUser", "").lower() == "yes",
        "user_override_declared": bool(props.get("User", "").strip()),
        "pre_post_or_condition_hooks": any(bool(props.get(p, "").strip()) for p in ("ExecStartPre", "ExecStartPost", "ExecCondition")),
    }


def inspect() -> dict[str, bool]:
    env = {"PATH": "/usr/bin:/bin", "LANG": "C"}
    for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
        if key in os.environ:
            env[key] = os.environ[key]
    result = subprocess.run(
        ["systemctl", "--user", "show", UNIT,
         "--property=" + ",".join(PROPS), "--no-pager"],
        check=False, capture_output=True, text=True, timeout=8, env=env,
    )
    if result.returncode:
        raise ValueError("systemd unavailable")
    props = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            raise ValueError("unexpected systemd output")
        key, value = line.split("=", 1)
        if key not in PROPS or key in props:
            raise ValueError("unexpected systemd property")
        props[key] = value
    if set(props) != set(PROPS):
        raise ValueError("incomplete systemd metadata")
    return classify(props, Path.home() / ".local/bin/bob-activity-manager")


def main() -> int:
    try:
        results = inspect()
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print("v0.7.1 EFFECTIVE UNIT INSPECTION: REFUSED")
        print("No service settings or installed files changed.")
        return 1
    for key, value in results.items():
        print(f"{key}: {'YES' if value else 'NO'}")
    print("v0.7.1 EFFECTIVE UNIT INSPECTION: COMPLETED (read-only)")
    print("No raw paths, arguments or environment values printed. Not deployment approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
