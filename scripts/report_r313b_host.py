#!/usr/bin/env python3
"""R3.13b fixed-host source attestation + explicit private-copy upgrade lab.

No production DDL, setting changes, tokens, external requests, unit writes,
publisher switch, R3 owner-UI endpoint, or release install. The --private-copy
flag only migrates a temporary SQLite online backup of the current queue.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import pwd
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from bob_v08.r313a_private_migration import (
    _history_counts, _history_digest, _private, _shape, inspect_boundary,
)
from bob_v08.r313b_install_attestation import attest
from bob_v08.r313b_upgrade_contract import (
    LAB_DIR, LAB_FILE, LAB_MARKER, LAB_MARKER_VALUE, OFF_SETTINGS,
    code_only_rollback_review, owner_controls, upgrade_private_copy,
)
from report_r3_cutover_inventory import QUEUE, PAUSED
from report_r38_effective_units import _cat


def _private_upgrade_rehearsal(source: Path) -> dict:
    """SQLite online backup; every DDL/DML change confined to disposable copy."""
    with tempfile.TemporaryDirectory(prefix="bob-r313b-") as temp:
        lab = Path(temp) / LAB_DIR
        lab.mkdir(mode=0o700)
        marker = lab / LAB_MARKER
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(LAB_MARKER_VALUE)
        copy_path = lab / LAB_FILE
        fd = os.open(copy_path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
        if not all(_private(p, directory=d, uid=os.geteuid()) for p, d in (
                (lab, True), (marker, False), (copy_path, False))):
            raise ValueError("private_upgrade_copy_untrusted")
        with closing(sqlite3.connect(source.absolute().as_uri() + "?mode=ro",
                                     uri=True, timeout=5)) as live:
            live.execute("PRAGMA query_only=ON")
            with closing(sqlite3.connect(copy_path, timeout=5,
                                         isolation_level=None)) as copy:
                live.backup(copy, pages=64, sleep=0.02)
                if not _shape(copy) or copy.execute(
                        "PRAGMA quick_check(1)").fetchone() != ("ok",):
                    raise ValueError("private_copy_schema_failed")
                old_digest = _history_digest(copy)
                old_counts = _history_counts(copy)
                crash_rolled_back = False
                try:
                    upgrade_private_copy(copy, inject_crash=True)
                except RuntimeError as exc:
                    crash_rolled_back = str(exc) == "r313b_synthetic_crash_before_commit"
                if not crash_rolled_back or _history_digest(copy) != old_digest:
                    raise ValueError("crash_rollback_did_not_preserve_history")
                first = upgrade_private_copy(copy)
                second = upgrade_private_copy(copy)
                if (not first["schema_added"] or second["schema_added"]
                        or second["historical_attempts"] != old_counts[1]
                        or owner_controls(copy) != {
                            "manual": "off", "automatic": "off", "authority": "none"}):
                    raise ValueError("upgrade_idempotence_or_default_off_failed")
                for key, value in OFF_SETTINGS.items():
                    if copy.execute(
                        "SELECT value FROM publish_settings WHERE name=?",
                        (key,)).fetchone() != (value,):
                        raise ValueError("owner_off_setting_changed")
                # Simulate activity AFTER upgrade. Code rollback must leave
                # newer attempts and uncertain outcomes in place.
                run_id = "20991231T235959Z"
                if copy.execute(
                        "SELECT 1 FROM publish_jobs WHERE run_id=?",
                        (run_id,)).fetchone():
                    raise ValueError("synthetic_recovery_run_collision")
                copy.execute(
                    "INSERT INTO publish_jobs (run_id,approval_sha256,post_id,"
                    "draft_comment,mode,state,created_at,attempted_at,updated_at)"
                    " VALUES(?,?,?,?,'manual','uncertain',?,?,?)",
                    (run_id, "f"*64, "ffffffff-ffff-4fff-8fff-ffffffffffff",
                     "PRIVATE REHEARSAL ONLY - no public send",
                     "2099-12-31T23:59:59Z", "2099-12-31T23:59:59Z",
                     "2099-12-31T23:59:59Z"))
                now_counts = _history_counts(copy)
                rollback = code_only_rollback_review(copy)
                if (now_counts[1] != old_counts[1] + 1 or
                        now_counts[2] != old_counts[2] + 1 or
                        rollback["database_restore_allowed"] or
                        rollback["retained_attempts"] != now_counts[1] or
                        rollback["retained_uncertain"] != now_counts[2]):
                    raise ValueError("code_only_recovery_lost_attempted_history")
                return {
                    "private_upgrade": "PASS",
                    "additive_schema": "R3.5_compatible",
                    "default_off_owner_controls": True,
                    "crash_rollback": True,
                    "idempotent": True,
                    "original_history_preserved_before_simulated_activity": True,
                    "original_attempts": old_counts[1],
                    "original_uncertain": old_counts[2],
                    "post_upgrade_synthetic_attempt_retained": True,
                    "code_only_rollback_preserved_new_history": True,
                    "database_restore_allowed": False,
                    "temporary_copy_deleted": True,
                    "live_database_modified": False,
                    "publisher_modified": False,
                    "r3_dispatch_authorized": False,
                    "cutover_authorized": False,
                }


def collect(*, private_copy: bool = False, unit_reader=_cat) -> dict:
    home = Path.home()
    account_ok = (pwd.getpwuid(os.geteuid()).pw_dir == str(home))
    boundary = inspect_boundary(home=home, queue=QUEUE, paused=PAUSED,
                                uid=os.geteuid())
    if not account_ok:
        boundary["review_blockers"] = sorted(set(
            boundary["review_blockers"] + ["account_home_mismatch"]))
        boundary["private_copy_eligible"] = False
    evidence = attest(
        unit_reader=unit_reader, uid=os.geteuid(), home=home,
        candidate_source=ROOT / "src/bin/bob-moltbook-publisher")
    rehearsal = "not_requested"
    if private_copy:
        if not boundary["private_copy_eligible"]:
            rehearsal = "refused_host_boundary"
        else:
            try:
                rehearsal = _private_upgrade_rehearsal(QUEUE)
            except (OSError, ValueError, RuntimeError, sqlite3.Error):
                rehearsal = "failed_closed"
    return {
        "format": "bob-r313b-host-source-only-v1",
        "host": boundary,
        "installed_publisher": evidence,
        "rehearsal": rehearsal,
        "installed_release_modified": False,
        "installed_owner_controls_modified": False,
        "live_schema_modified": False,
        "new_r3_dispatch_authorized": False,
        "cutover_authorized": False,
    }


def compact(data: dict) -> str:
    boundary = data["host"]
    evidence = data["installed_publisher"]
    rehearsal = data["rehearsal"]
    lines = [
        "R3.13b INSTALLED SOURCE / PRIVATE UPGRADE (no cutover)",
        "trusted queue boundary: " + ("yes" if boundary["private_copy_eligible"] else "no"),
        "legacy schema: " + boundary["legacy_schema"],
        "R3 installed owner settings: " + boundary["r3_settings"],
        "effective publisher unit: " + evidence["effective_unit_shape"],
        "publisher executable: " + evidence["installed_file"],
        "updater registry check: " + evidence["updater_registry"],
        "installed versus next source: " + evidence["current_next_candidate_match"],
        "boundary blockers: " + (", ".join(boundary["review_blockers"]) or "none"),
        "source review blockers: " + (", ".join(evidence["review_blockers"]) or "none"),
    ]
    if isinstance(rehearsal, dict):
        lines += [
            "private-copy schema/owner-Off upgrade: " + rehearsal["private_upgrade"],
            "crash rollback: " + str(rehearsal["crash_rollback"]),
            "repeat migration: " + str(rehearsal["idempotent"]),
            "existing history preserved: " + str(
                rehearsal["original_history_preserved_before_simulated_activity"]),
            "historical send attempts: " + str(rehearsal["original_attempts"]),
            "historical uncertain outcomes: " + str(rehearsal["original_uncertain"]),
            "post-upgrade synthetic uncertain attempt retained: " + str(
                rehearsal["post_upgrade_synthetic_attempt_retained"]),
            "code-only rollback preserved history: " + str(
                rehearsal["code_only_rollback_preserved_new_history"]),
            "private copy: deleted",
        ]
    else:
        lines += ["private-copy upgrade rehearsal: " + rehearsal]
    return "\n".join(lines + [
        "live database changed: NO", "installed publisher changed: NO",
        "R3 manual/auto publication rights: NONE", "R3 cutover authorized: NO",
    ])


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    if args not in ([], ["--json"], ["--private-copy"],
                    ["--private-copy", "--json"]):
        print("Usage: python3 scripts/report_r313b_host.py "
              "[--private-copy] [--json]")
        return 2
    if os.geteuid() == 0:
        print("R3.13b HOST: refuse root")
        return 1
    result = collect(private_copy="--private-copy" in args)
    print(json.dumps(result, sort_keys=True, indent=2) if "--json" in args
          else compact(result))
    if "--private-copy" in args and not (
            isinstance(result["rehearsal"], dict) and
            result["rehearsal"].get("private_upgrade") == "PASS"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
