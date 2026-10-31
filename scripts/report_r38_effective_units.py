#!/usr/bin/env python3
"""R3.8 READ-ONLY effective publisher service/timer inspection.

Only `systemctl --user cat` for two fixed installed legacy unit names.
Never show raw unit content, ExecStart paths, Environment, credentials, file
paths or drop-in bodies. Never install, start, stop, reload or enable units.
An inconclusive report is a REVIEW BLOCKER, not an authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import shlex
import subprocess
import sys

SERVICE = "bob-moltbook-publisher.service"
TIMER = "bob-moltbook-publisher.timer"
MAX_RAW = 128 * 1024
TIMING = frozenset(("OnCalendar", "OnBootSec", "OnStartupSec",
                    "OnUnitActiveSec", "OnUnitInactiveSec"))
EXEC_BLOCKERS = frozenset(("ExecStartPre", "ExecStartPost",
                           "ExecStopPost", "ExecCondition"))
ENV_KEYS = frozenset(("Environment", "EnvironmentFile", "PassEnvironment",
                      "LoadCredential", "SetCredential", "SetCredentialEncrypted"))
EXTRA_KEYS = frozenset(("Unit", "Type", "ExecStart", "Restart", "PartOf", "BindsTo"))
SAFE_SIMPLE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
DANGEROUS = re.compile(r"[\n\r\x00\x01-\x1f\x7f;|&<>$\x60%]")


@dataclass(frozen=True)
class Audit:
    service_valid: bool
    timer_valid: bool
    blockers: tuple[str, ...]
    service_dropins: int
    timer_dropins: int
    environment_directives: int
    authority: str = "read_only_evidence"
    cutover_authorized: bool = False
    modifies_host: bool = False


def _effective(raw: str, section: str):
    """Conservative section-specific systemd replacement/reset semantics."""
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_RAW:
        raise ValueError("unit_text_unavailable")
    entries = []
    active = ""
    dropins = 0
    for line in raw.splitlines():
        if line.startswith("# ") and (".service.d/" in line or ".timer.d/" in line):
            dropins += 1
        item = line.strip()
        if not item or item.startswith(("#", ";")):
            continue
        if item.startswith("[") and item.endswith("]"):
            active = item[1:-1]
            continue
        if active != section:
            continue
        key, sep, value = item.partition("=")
        key = key.strip()
        if sep and SAFE_SIMPLE.fullmatch(key):
            entries.append((key, value.strip()))
        else:
            raise ValueError("unrecognized_unit_directive")
    return entries, dropins


def _safe_executable(command: str) -> bool:
    # systemd's ExecStart language is richer than shell; accept only a narrow
    # ordinary Python invocation or direct publisher binary. Everything else
    # needs human review, even if systemd would accept it.
    if not command or DANGEROUS.search(command):
        return False
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return False
    if len(argv) == 1:
        return argv[0].split("/")[-1] == "bob-moltbook-publisher"
    if len(argv) != 2:
        return False
    python = argv[0].split("/")[-1]
    script = argv[1].split("/")[-1]
    return python in ("python3", "python3.11", "python3.12", "python3.13", "python3.14") and (
        script == "bob-moltbook-publisher")


def audit(service_text: str, timer_text: str) -> Audit:
    blockers = []
    env_total = 0
    try:
        service, service_dropins = _effective(service_text, "Service")
    except (ValueError, UnicodeError):
        service, service_dropins = [], 0
        blockers.append("publisher_service_text_unavailable")
    try:
        timer, timer_dropins = _effective(timer_text, "Timer")
    except (ValueError, UnicodeError):
        timer, timer_dropins = [], 0
        blockers.append("publisher_timer_text_unavailable")
    service_type = []
    commands = []
    for k, v in service:
        if k == "ExecStart":
            if not v:
                commands = []  # systemd empty reset in a drop-in
            else:
                commands.append(v)
        elif k == "Type":
            service_type.append(v)
        elif k == "Restart":
            if v != "no":
                blockers.append("publisher_restart_policy_needs_review")
        elif k in EXEC_BLOCKERS:
            if v:
                blockers.append("extra_publisher_process_command")
        elif k in ENV_KEYS:
            env_total += 1
        elif k in ("User", "Group", "PermissionsStartOnly"):
            blockers.append("publisher_execution_identity_needs_review")
    if not service:
        blockers.append("publisher_service_no_effective_directives")
    if not service_type or service_type[-1] != "oneshot":
        blockers.append("publisher_not_verified_oneshot")
    if len(commands) != 1 or not _safe_executable(commands[0]):
        blockers.append("publisher_exec_not_verified")
    timer_target = []
    cadence = []
    for k, v in timer:
        if k == "Unit":
            timer_target.append(v)
        if k in TIMING:
            if not v:
                cadence = [x for x in cadence if x[0] != k]  # timer reset
            else:
                cadence.append((k, v))
        if k in ("OnActiveSec", "OnUnitActiveUSec"):
            blockers.append("timer_timing_unreviewed")
    if not timer:
        blockers.append("publisher_timer_no_effective_directives")
    if not timer_target or timer_target[-1] != SERVICE:
        blockers.append("publisher_timer_wrong_target")
    if not cadence:
        blockers.append("publisher_timer_no_schedule")
    # A unit can have multiple drop-ins: report their count, never their names.
    service_ok = not any(b.startswith("publisher_") or
                         b in ("extra_publisher_process_command",)
                         for b in blockers)
    timer_ok = not any(b.startswith("timer_") for b in blockers) and (
        "publisher_timer_wrong_target" not in blockers and
        "publisher_timer_no_schedule" not in blockers and
        "publisher_timer_no_effective_directives" not in blockers)
    return Audit(
        service_valid=service_ok, timer_valid=timer_ok,
        blockers=tuple(sorted(set(blockers))),
        service_dropins=service_dropins,
        timer_dropins=timer_dropins,
        environment_directives=env_total)


def _cat(unit: str, *, run=subprocess.run) -> str:
    if unit not in (SERVICE, TIMER):
        raise ValueError("unapproved_unit")
    try:
        completed = run(
            ["systemctl", "--user", "cat", unit],
            capture_output=True, text=True, timeout=4, check=False)
        if completed.returncode or not isinstance(completed.stdout, str):
            return ""
        if len(completed.stdout.encode("utf-8")) > MAX_RAW:
            return ""
        return completed.stdout
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        return ""


def report(*, run=subprocess.run):
    data = audit(_cat(SERVICE, run=run), _cat(TIMER, run=run))
    return {
        "format": "bob-r38-effective-unit-audit-v1",
        "effective_service": "reviewed_shape" if data.service_valid else "unverified",
        "effective_timer": "reviewed_shape" if data.timer_valid else "unverified",
        "service_dropins": data.service_dropins,
        "timer_dropins": data.timer_dropins,
        "environment_declarations": data.environment_directives,
        "review_blockers": list(data.blockers),
        "cutover_authorized": False,
        "service_changes": 0,
        "live_publishes": 0,
    }


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    if args not in ([], ["--json"]):
        print("Usage: python3 scripts/report_r38_effective_units.py [--json]")
        return 2
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("R3.8 UNIT AUDIT: refuse root")
        return 1
    data = report()
    if args == ["--json"]:
        print(json.dumps(data, sort_keys=True, indent=2))
    else:
        print("R3.8 EFFECTIVE PUBLISHER UNITS (read-only)")
        for key in ("effective_service", "effective_timer", "service_dropins",
                    "timer_dropins", "environment_declarations"):
            print(key.replace("_", " ") + ":", data[key])
        print("review blockers:", ", ".join(data["review_blockers"]) or "none")
        print("R3 cutover authorized: NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
