#!/usr/bin/env python3
"""Read-only v0.7.1 effective systemd launch contract preflight.

Never print ExecStart, Environment, WorkingDirectory, paths, or secret values.
Does not approve a deployment or modify any service.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

from preflight_v071_live import EXPECTED_MANAGER_SHA256, check_manager, check_backup

UNIT = "bob-activity-manager.service"
KEYS = ("LoadState", "ActiveState", "SubState", "FragmentPath", "DropInPaths",
        "ExecStart", "WorkingDirectory", "Environment", "EnvironmentFiles",
        "ExecStartPre", "ExecStartPost", "ExecCondition", "User", "DynamicUser",
        "RootDirectory", "RootImage")
REQUIRED = set(KEYS)
# systemctl show can omit unset optional properties on some systemd versions.
OPTIONAL_EMPTY = {"EnvironmentFiles", "ExecStartPre", "ExecStartPost", "ExecCondition"}


def classify(raw: str, *, manager: Path) -> dict[str, bool]:
    if not raw or len(raw) > 256 * 1024 or "\x00" in raw:
        raise ValueError("invalid systemd output")
    values = {}
    for line in raw.splitlines():
        if "=" not in line:
            raise ValueError("malformed systemd output")
        key, value = line.split("=", 1)
        if key not in REQUIRED or key in values:
            raise ValueError("unexpected or repeated property")
        values[key] = value
    missing = REQUIRED - set(values)
    if missing - OPTIONAL_EMPTY:
        raise ValueError("missing_properties:" + ",".join(sorted(missing - OPTIONAL_EMPTY)))
    for key in missing:
        values[key] = ""
    # Fail closed for any surprising execution envelope. ExecStart is
    # systemd's rendered string, so this check only asserts one expected
    # absolute executable token, never a fully parsed service grammar.
    command = values["ExecStart"]
    expected = str(manager)
    executable_match = (
        command.count("{ path=") == 1 and
        ("{ path=" + expected + " ;") in command and
        ("argv[]=" + expected) in command and
        " ; ignore_errors=no" in command
    )
    return {
        "loaded_running": (values["LoadState"], values["ActiveState"], values["SubState"])
                           == ("loaded", "active", "running"),
        "pinned_installed_executable": check_manager(manager),
        "effective_execstart_expected": executable_match,
        "effective_working_directory_present": bool(values["WorkingDirectory"])
                                               and values["WorkingDirectory"].startswith("/"),
        "effective_inline_environment_present": bool(values["Environment"]),
        "dropin_inventory_available": bool(values["FragmentPath"]),
        "no_extra_exec_hooks": not any(values[k] for k in
                                       ("ExecStartPre", "ExecStartPost", "ExecCondition")),
        "no_environment_file": not values["EnvironmentFiles"],
        "no_dynamic_or_root_redirect": values["DynamicUser"] == "no"
            and not values["RootDirectory"] and not values["RootImage"],
        "user_service_scope": not values["User"],
    }


def query() -> str:
    env = {"PATH": "/usr/bin:/bin", "LANG": "C"}
    for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
        if key in os.environ:
            env[key] = os.environ[key]
    result = subprocess.run(
        ["systemctl", "--user", "show", UNIT,
         "--property=" + ",".join(KEYS), "--no-pager"],
        capture_output=True, text=True, timeout=8, env=env, check=False)
    if result.returncode:
        raise ValueError("systemd inventory unavailable")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True, type=Path)
    args = parser.parse_args()
    manager = Path.home() / ".local/bin/bob-activity-manager"
    try:
        results = classify(query(), manager=manager)
        results["recent_private_backup"] = check_backup(args.backup.expanduser())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        # Only static reason codes/property NAMES. Never expose raw systemctl output.
        if isinstance(exc, ValueError) and str(exc).startswith("missing_properties:"):
            reason = str(exc)
        elif isinstance(exc, subprocess.TimeoutExpired):
            reason = "systemd_query_timeout"
        elif isinstance(exc, OSError):
            reason = "systemd_query_os_error"
        else:
            reason = "systemd_response_invalid"
        print("preflight_refusal_reason:", reason)
        print("v0.7.1 EFFECTIVE SERVICE PREFLIGHT: REFUSED")
        return 1
    for key, passed in results.items():
        print(key + ":", "PASS" if passed else "REFUSED")
    print("v0.7.1 EFFECTIVE SERVICE PREFLIGHT:",
          "PASS" if all(results.values()) else "REFUSED")
    print("Read-only inspection. No systemd changes, database writes or release switch.")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
