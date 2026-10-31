#!/usr/bin/env python3
"""G2 read-only OMEN/OpenClawLab startup and replay-risk observation.

This is NOT a reboot controller, publisher simulator, credential rotation,
database snapshot writer, proof of WAN isolation, or authorization to publish.
Runs existing exact-host HTTPS/R3 checks, fixed systemd metadata probes and a
read-only SQLite schema/count check. Prints no passwords, settings values,
post/comment text, unit bodies, ExecStart, environment or private file paths.
The before/after results require an external, owner-confirmed reboot event and
source-linked ledger/receipt review to establish actual G2 acceptance.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT / "src/lib/bob")]

import report_ch_https3_cutover as https
import report_r38_effective_units as publisher
import report_r3_cutover_inventory as inventory
import r313d_live_off_migration as migration
import report_service_readiness as startup

REQUIRED_ACTIVE = (
    ("user", "bob-activity-manager.service"),
    ("user", "bob-moltbook-publisher.timer"),
    ("user", "bob-moltbook-scout.timer"),
)
REQUIRED_INERT = (
    ("system", "bob-moltbook-scout.timer"),
    ("system", "bob-moltbook-scout.service"),
    ("user", "bob-r3-candidate-publisher.timer"),
    ("user", "bob-r3-candidate-publisher.service"),
)
ALL_UNITS = REQUIRED_ACTIVE + REQUIRED_INERT
ALLOWED_ENABLED = ("enabled", "enabled-runtime")
INERT_ENABLED = ("disabled", "masked", "masked-runtime", "unknown")
PHASES = ("baseline", "postcheck")


def _operator() -> bool:
    try:
        user = pwd.getpwuid(os.geteuid())
        return os.geteuid() != 0 and user.pw_name == "openclaw" and (
            user.pw_dir == str(Path.home()))
    except (OSError, KeyError, ValueError):
        return False


def _facts(scope: str, unit: str) -> dict:
    if (scope, unit) not in ALL_UNITS:
        raise ValueError("unreviewed_g2_unit")
    row = inventory.unit_facts(scope, unit)
    return {key: row.get(key, "unknown") for key in (
        "scope", "unit", "load", "active", "enabled")}


def _inert(row: dict) -> bool:
    """A service/timer absent at boot is okay; an enabled unit is not."""
    return ((row["load"] == "not-found" and row["active"] == "inactive")
            or (row["active"] == "inactive"
                and row["enabled"] in ("disabled", "masked", "masked-runtime")))


def _inert_competitor(scope: str, unit: str, states: dict) -> bool:
    """Narrow exception for the observed disabled system Scout timer.

    A static service lacks an ordinary enable target; that does NOT make it
    impossible to start through another dependency or manual activation.
    Accept only THIS named inactive system Scout service while its associated
    installed system timer is demonstrably disabled AND inactive. Other
    static services, static timers, active services and unknown states fail.
    This is a host baseline gate, never proof of external no-duplicate posts.
    """
    key = (scope, unit)
    if key not in REQUIRED_INERT or key not in states:
        return False
    row = states[key]
    if _inert(row):
        return True
    if key != ("system", "bob-moltbook-scout.service"):
        return False
    timer = states.get(("system", "bob-moltbook-scout.timer"), {})
    return (
        row["load"] == "loaded"
        and row["active"] == "inactive"
        and row["enabled"] == "static"
        and timer.get("load") == "loaded"
        and timer.get("active") == "inactive"
        and timer.get("enabled") in ("disabled", "masked", "masked-runtime")
    )


def inspect(phase: str) -> dict:
    if phase not in PHASES:
        raise ValueError("unsupported_g2_phase")
    operator = _operator()
    tls = {}
    units = []
    unit_gate = False
    publisher_gate = False
    history = {"state": "unverified", "attempts": None, "uncertain": None}
    journal = "unverified"
    linger = "unavailable"
    if operator:
        try:
            tls = https.inspect("installed")
        except (OSError, ValueError, KeyError, TypeError):
            tls = {}
        try:
            units = [_facts(scope, name) for scope, name in ALL_UNITS]
            by_name = {(row["scope"], row["unit"]): row for row in units}
            required = all(
                by_name[(scope, unit)]["load"] == "loaded"
                and by_name[(scope, unit)]["active"] == "active"
                for scope, unit in REQUIRED_ACTIVE
            )
            timers_enabled = all(
                by_name[("user", name)]["enabled"] in ALLOWED_ENABLED
                for name in ("bob-moltbook-publisher.timer",
                             "bob-moltbook-scout.timer"))
            no_extra_writers = all(
                _inert_competitor(scope, unit, by_name)
                for scope, unit in REQUIRED_INERT)
            unit_gate = required and timers_enabled and no_extra_writers
        except (OSError, ValueError, KeyError, TypeError):
            units = []
        try:
            p = publisher.report()
            publisher_gate = (
                p["effective_service"] == "reviewed_shape"
                and p["effective_timer"] == "reviewed_shape"
                and p["review_blockers"] == [])
        except (OSError, ValueError, KeyError, TypeError):
            publisher_gate = False
        try:
            raw = migration._db_review()
            history = {
                "state": raw.get("state", "unverified"),
                "attempts": raw.get("attempts"),
                "uncertain": raw.get("uncertain"),
            }
            journal = migration._journal_state()
        except (OSError, ValueError, KeyError, TypeError):
            pass
        try:
            linger = startup.linger_status()
        except (OSError, ValueError, KeyError, TypeError):
            pass
    history_valid = (
        history["state"] == "ready"
        and type(history["attempts"]) is int and history["attempts"] >= 0
        and type(history["uncertain"]) is int and history["uncertain"] >= 0
        and journal == "complete")
    accepted = (operator and tls.get("acceptance") == "PASS"
                and unit_gate and publisher_gate and history_valid)
    return {
        "format": "bob-g2-host-observation-v1",
        "phase": phase,
        "authority": "read_only_observation",
        "account": "verified" if operator else "unverified",
        "installed_https_r3_off": ("PASS" if tls.get("acceptance") == "PASS"
                                   else "NOT_VERIFIED"),
        "expected_user_units_and_inert_competitors": (
            "PASS" if unit_gate else "NOT_VERIFIED"),
        "effective_legacy_publisher": (
            "reviewed_shape" if publisher_gate else "unverified"),
        "legacy_history_schema_journal": (
            "verified" if history_valid else "unverified"),
        "historical_attempts": (history["attempts"] if history_valid else None),
        "historical_uncertain": (history["uncertain"] if history_valid else None),
        "user_linger": linger if linger in ("yes", "no") else "unavailable",
        "unit_states": units,
        "host_gate": "PASS" if accepted else "NOT_VERIFIED",
        "windows_startup_or_reboot_observed": False,
        "actual_duplicate_posting_excluded": False,
        "cross_reboot_ledger_comparison": "not_performed",
        "lan_only_wan_exposure_verified": False,
        "live_systemd_or_windows_changes": 0,
        "database_or_credentials_changed": False,
        "moltbook_requests": 0,
        "r3_public_send_authorized": False,
    }


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args not in (["--baseline"], ["--postcheck"],
                    ["--baseline", "--json"], ["--postcheck", "--json"]):
        print("Usage: python3 scripts/report_g2_recovery.py "
              "[--baseline | --postcheck] [--json]")
        return 2
    if not _operator():
        print("G2 HOST REPORT REFUSED: expected normal openclaw account")
        return 1
    phase = "baseline" if args[0] == "--baseline" else "postcheck"
    try:
        report = inspect(phase)
    except (OSError, ValueError, TypeError, KeyError):
        report = {"format": "bob-g2-host-observation-v1", "phase": phase,
                  "host_gate": "NOT_VERIFIED",
                  "r3_public_send_authorized": False}
    if "--json" in args:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print("G2 " + phase.upper() + " (READ ONLY)")
        for key in ("account", "installed_https_r3_off",
                    "expected_user_units_and_inert_competitors",
                    "effective_legacy_publisher",
                    "legacy_history_schema_journal", "historical_attempts",
                    "historical_uncertain", "user_linger", "host_gate"):
            print(key.replace("_", " ") + ":", report.get(key, "unverified"))
        print("Windows reboot observed by report: NO")
        print("External duplicate posting ruled out by report: NO")
        print("Database, systemd, Windows and credentials changed: NO")
        print("R3 real publishing authorized: NO")
    return 0 if report["host_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
