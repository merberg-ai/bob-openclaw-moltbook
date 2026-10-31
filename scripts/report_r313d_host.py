#!/usr/bin/env python3
"""R3.13d stage-one read-only host audit and explicit private-copy rollout.

NO production DDL, install, owner settings mutation, unit action, credential
read, HTTP or POST. The only DDL is inside a deleted 0600 SQLite online
backup under a private 0700 temporary directory after an explicit flag.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT/"src"), str(ROOT/"src"/"lib"/"bob"), str(ROOT/"scripts"),
]

import report_r313b_host as prior
from bob_v08.r313a_private_migration import (
    _history_counts, _history_digest, _private, _shape, MAX_QUEUE_BYTES,
)
from bob_v08.r313b_upgrade_contract import (
    LAB_FILE, LAB_DIR, LAB_MARKER, LAB_MARKER_VALUE,
    code_only_rollback_review, upgrade_private_copy,
)
from bob_v08.r313d_staging import (
    source_off_gate, migrate_marked_copy, _schema_shape, _off,
)


def _private_copy_staged(source: Path) -> dict:
    """Copy committed WAL safely, then test crash/repeat/recovery on copy."""
    with tempfile.TemporaryDirectory(prefix="bob-r313d-stage-") as temp:
        root = Path(temp)
        lab = root/LAB_DIR
        lab.mkdir(mode=0o700)
        marker = lab/LAB_MARKER
        marker_fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(marker_fd, "w", encoding="ascii") as stream:
            stream.write(LAB_MARKER_VALUE)
        target = lab/LAB_FILE
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
        if not all(_private(path, directory=directory, uid=os.geteuid())
                   for path, directory in (
                       (root, True), (lab, True),
                       (marker, False), (target, False))):
            raise ValueError("staging_snapshot_not_private")
        with closing(sqlite3.connect(source.absolute().as_uri()+"?mode=ro",
                                     uri=True, timeout=5)) as live:
            live.execute("PRAGMA query_only=ON")
            with closing(sqlite3.connect(target, timeout=5,
                                         isolation_level=None)) as copy:
                live.backup(copy, pages=64, sleep=0.02)
                if (not _shape(copy)
                        or copy.execute("PRAGMA quick_check(1)").fetchone() != ("ok",)):
                    raise ValueError("private_snapshot_legacy_schema_bad")
                initial = _history_digest(copy)
                counts = _history_counts(copy)
                upgrade_private_copy(copy)  # exact R3.13b OFF schema on copy
                post_b = _history_digest(copy)
                if not _off(copy):
                    raise ValueError("new_owner_controls_not_off")
                interrupted = False
                try:
                    migrate_marked_copy(copy, inject_crash=True)
                except RuntimeError as exc:
                    interrupted = str(exc) == "r313d_synthetic_crash_before_commit"
                if (not interrupted or _schema_shape(copy) != "absent"
                        or _history_digest(copy) != post_b):
                    raise ValueError("envelope_schema_crash_rollback_failed")
                first = migrate_marked_copy(copy)
                second = migrate_marked_copy(copy)
                if (not first["schema_added"] or second["schema_added"]
                        or _schema_shape(copy) != "match"
                        or _history_digest(copy) != post_b or not _off(copy)):
                    raise ValueError("envelope_schema_idempotence_or_history_failed")
                # Compare original historical rows excluding the four brand-new
                # default-Off settings. Never erase real existing rows.
                changed_settings = copy.execute(
                    "SELECT name FROM publish_settings WHERE name LIKE 'r3_%'"
                ).fetchall()
                if len(changed_settings) != 4:
                    raise ValueError("unexpected_r3_settings")
                if counts != _history_counts(copy):
                    raise ValueError("historical_attempts_changed")

                # After a staged migration, a synthetic uncertain event must
                # never be discarded by a code-only rollback.
                run = "20991231T235959Z"
                if copy.execute("SELECT 1 FROM publish_jobs WHERE run_id=?",
                                (run,)).fetchone():
                    raise ValueError("synthetic_run_collision")
                copy.execute(
                    "INSERT INTO publish_jobs (run_id,approval_sha256,post_id,"
                    "draft_comment,mode,state,created_at,attempted_at,updated_at)"
                    "VALUES(?,?,?,?,'manual','uncertain',?,?,?)",
                    (run,"f"*64,"ffffffff-ffff-4fff-8fff-ffffffffffff",
                     "SYNTHETIC PRIVATE TEST NO POST",
                     "2099-12-31T23:59:59Z",
                     "2099-12-31T23:59:59Z",
                     "2099-12-31T23:59:59Z"))
                after = _history_counts(copy)
                rollback = code_only_rollback_review(copy)
                if (after[1] != counts[1]+1 or after[2] != counts[2]+1
                        or rollback["database_restore_allowed"]
                        or rollback["retained_attempts"] != after[1]
                        or rollback["retained_uncertain"] != after[2]):
                    raise ValueError("rollback_lost_new_uncertain_attempt")
                return {
                    "private_staged_upgrade": "PASS",
                    "r313b_owner_controls": "explicit_off",
                    "r313c_action_envelope_schema": "match",
                    "crash_rollback": True,
                    "idempotent": True,
                    "legacy_history_preserved": True,
                    "historical_attempts": counts[1],
                    "historical_uncertain": counts[2],
                    "new_synthetic_uncertain_attempt_retained": True,
                    "no_stale_database_restore": True,
                    "private_copy_deleted": True,
                    "live_database_changed": False,
                    "publisher_or_units_changed": False,
                    "r3_dispatch_enabled": False,
                    "cutover_authorized": False,
                }


def collect(*, private_copy=False, unit_reader=None) -> dict:
    kw = {} if unit_reader is None else {"unit_reader": unit_reader}
    base = prior.collect(private_copy=False, **kw)
    safe_source = source_off_gate(ROOT)
    host = base["host"]
    att = base["installed_publisher"]
    eligible = (
        host["private_copy_eligible"]
        and att["effective_unit_shape"] == "reviewed_shape"
        and att["installed_file"] == "owner_controlled_regular"
        and att["updater_registry"] == "verified_registry_hash"
        and not att["review_blockers"]
        and safe_source["production_off_source"]
        and host["legacy_schema"] == "match"
        and host["r3_settings"] in ("absent_off","explicit_off")
    )
    rehearsal = "not_requested"
    if private_copy:
        if not eligible:
            rehearsal = "refused_staging_boundary"
        else:
            try:
                rehearsal = _private_copy_staged(
                    Path.home()/".config/moltbook/activity-queue.sqlite3")
            except (OSError, RuntimeError, ValueError, sqlite3.Error):
                rehearsal = "failed_closed"
    return {
        "format": "bob-r313d-stage-off-v1",
        "host": host,
        "publisher": att,
        "reviewed_off_gates": safe_source,
        "eligible_for_private_stage": eligible,
        "rehearsal": rehearsal,
        "live_database_changed": False,
        "installed_files_changed": False,
        "owner_consent_changed": False,
        "units_changed": False,
        "moltbook_requests": 0,
        "r3_dispatch_authorized": False,
        "cutover_authorized": False,
    }


def compact(report: dict) -> str:
    host, att = report["host"], report["publisher"]
    rehearsal = report["rehearsal"]
    lines = [
        "R3.13d VERSIONED STAGING / PRIVATE UPGRADE (NO CUTOVER)",
        "trusted queue boundary: " + (
            "yes" if host["private_copy_eligible"] else "no"),
        "legacy schema: " + host["legacy_schema"],
        "installed R3 owner consent: " + host["r3_settings"],
        "installed publisher unit: " + att["effective_unit_shape"],
        "installed executable: " + att["installed_file"],
        "updater registry: " + att["updater_registry"],
        "source hard-Off gates: " + (
            "verified_three" if report["reviewed_off_gates"]["production_off_source"]
            else "unverified"),
        "staging eligible: " + (
            "yes" if report["eligible_for_private_stage"] else "no"),
        "boundary blockers: " + (",".join(host["review_blockers"]) or "none"),
        "source blockers: " + (",".join(att["review_blockers"]) or "none"),
    ]
    if isinstance(rehearsal, dict):
        lines += [
            "disposable schema upgrade: " + rehearsal["private_staged_upgrade"],
            "default R3 owner consent: explicit_off",
            "action-envelope schema: " + rehearsal["r313c_action_envelope_schema"],
            "crash rollback: True",
            "idempotent: True",
            "legacy history preserved: True",
            "historical attempts: " + str(rehearsal["historical_attempts"]),
            "historical uncertain: " + str(rehearsal["historical_uncertain"]),
            "synthetic uncertain attempt survives code-only rollback: True",
            "private copy: deleted",
        ]
    else:
        lines.append("private staged upgrade: " + rehearsal)
    return "\n".join(lines + [
        "live database modified: NO",
        "installed files or services modified: NO",
        "new R3 manual or automatic rights: NONE",
        "R3 real sending enabled: NO",
        "R3 cutover authorized: NO",
    ])


def main(args=None) -> int:
    args = sys.argv[1:] if args is None else args
    if args not in ([], ["--json"], ["--private-copy"],
                    ["--private-copy", "--json"]):
        print("Usage: python3 scripts/report_r313d_host.py "
              "[--private-copy] [--json]")
        return 2
    if os.geteuid() == 0:
        print("R3.13d refuses root")
        return 1
    outcome = collect(private_copy="--private-copy" in args)
    print(json.dumps(outcome,sort_keys=True,indent=2) if "--json" in args
          else compact(outcome))
    if "--private-copy" in args and not (
            isinstance(outcome["rehearsal"],dict)
            and outcome["rehearsal"].get("private_staged_upgrade") == "PASS"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
