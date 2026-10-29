#!/usr/bin/env python3
"""Read-only preflight for *future* stage-only systemd manager experiments.

All queried names are fixed, uniquely prefixed, synthetic unit names. No
systemd-run invocation, service registration, reload, enable/start/stop, port,
network, credential, or live database access. This does not grant permission
to execute transient services or prove network isolation.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from stage_service_graph import ORDER, PREFIX, TIMERS

SERVICE_NAMES = tuple(PREFIX + role + ".service" for role in ORDER)
TIMER_NAMES = tuple(PREFIX + role + ".timer" for role in TIMERS)
STAGE_NAMES = SERVICE_NAMES + TIMER_NAMES
PROPS = ("LoadState", "ActiveState", "UnitFileState")
UNAVAILABLE = "unavailable"


def safe_query(args: list[str]) -> subprocess.CompletedProcess | None:
    if not args or args[0] != "systemctl":
        raise ValueError("Only read-only systemctl queries are allowed")
    # fixed command grammar; no shell, arbitrary unit arguments or writes.
    if args == ["systemctl", "--user", "show", "--property=Version", "--no-pager"]:
        pass
    elif (len(args) == 6 and args[1] in {"--user", "--system"}
          and args[2] == "show" and args[3] in STAGE_NAMES
          and args[4] == "--property=LoadState,ActiveState,UnitFileState"
          and args[5] == "--no-pager"):
        pass
    else:
        raise ValueError("Non-read-only systemd command refused")
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=4, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def extract_status(result: subprocess.CompletedProcess | None) -> dict:
    if result is None or result.returncode != 0:
        return {"available": False, "absent": False}
    values = {}
    for line in result.stdout.splitlines():
        key, sep, val = line.partition("=")
        if sep and key in PROPS and key not in values:
            values[key] = val
    # Strict absence only. Masked/inactive/failed units are *not* safe reuse.
    absent = (values.get("LoadState") == "not-found"
              and values.get("ActiveState") == "inactive"
              and values.get("UnitFileState", "") in {"", "not-found"})
    return {"available": True, "absent": absent}


def query_preflight(run=safe_query) -> dict:
    runtime = run(["systemctl", "--user", "show",
                   "--property=Version", "--no-pager"])
    manager_ok = bool(
        runtime is not None and runtime.returncode == 0
        and any(line.startswith("Version=") and len(line) > 8
                for line in runtime.stdout.splitlines())
    )
    states = {}
    for scope in ("--user", "--system"):
        for name in STAGE_NAMES:
            state = extract_status(run([
                "systemctl", scope, "show", name,
                "--property=LoadState,ActiveState,UnitFileState", "--no-pager",
            ]))
            states[(scope, name)] = state
    unavailable = sum(not s["available"] for s in states.values())
    collisions = sum(s["available"] and not s["absent"] for s in states.values())
    binaries = all(shutil.which(x) is not None for x in
                   ("systemctl", "systemd-run", "systemd-analyze"))
    all_names_scoped = (len(STAGE_NAMES) == 10
                        and len(set(STAGE_NAMES)) == 10
                        and all(n.startswith(PREFIX) for n in STAGE_NAMES))
    return {
        "user_systemd_manager_reachable": manager_ok,
        "stage_unit_names_checked": len(states),
        "colliding_or_reserved_names": collisions,
        "unavailable_name_queries": unavailable,
        "required_tools_detected": binaries,
        "unique_stage_names_only": all_names_scoped,
        "ready_for_separate_stage_execution_review": (
            manager_ok and not unavailable and not collisions
            and binaries and all_names_scoped
        ),
        "live_install_modified": False,
    }


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("SYSTEMD STAGING PREFLIGHT: REFUSED (root user)", file=sys.stderr)
        return 1
    try:
        result = query_preflight()
    except (OSError, ValueError, RuntimeError) as exc:
        print("SYSTEMD STAGING PREFLIGHT: REFUSED", type(exc).__name__,
              "(no live services changed)", file=sys.stderr)
        return 1
    print("SYSTEMD STAGING PREFLIGHT:",
          "PASS" if result["ready_for_separate_stage_execution_review"] else "NOT READY")
    for key, value in result.items():
        print(" ", key + ":", value)
    print("No units installed, enabled, registered, started, stopped or restarted.")
    print("This is a READ-ONLY preflight, NOT authorization to run transient units.")
    return 0 if result["ready_for_separate_stage_execution_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
