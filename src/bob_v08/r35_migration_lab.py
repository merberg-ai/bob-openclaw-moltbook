"""R3.5 isolated *additive* migration and fail-closed restart rehearsal.

This module refuses the installed activity-queue.sqlite3 and any unmarked
fixture. It has no live entrypoint, publisher/network clients, or systemd
operations. The legacy publisher remains the only real credentialed writer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3

from .r3_cutover_rehearsal import CutoverState

FOLDER = "r35-inert-fixtures"
FILENAME = "r35-legacy-queue-lab.sqlite3"
MARKER = "r35-legacy-schema-synthetic-only-v1"
SCHEMA = "r35-additive-draft-v1"
REQUIRED = {
    "publish_jobs": frozenset((
        "run_id", "approval_sha256", "post_id", "draft_comment", "mode",
        "state", "created_at", "attempted_at", "updated_at")),
    "decisions": frozenset(("run_id", "draft_sha256", "status", "decided_at")),
    "publish_settings": frozenset(("name", "value")),
}
NEW = {
    "r3_proposals": frozenset((
        "source_run", "post_id", "draft_comment", "seal_sha256", "fingerprint",
        "snapshot_sha256", "state", "created_at", "updated_at")),
    "r3_owner_approvals": frozenset((
        "source_run", "seal_sha256", "decision", "at")),
    "r3_lab_audit": frozenset(("id", "source_run", "event", "reason", "at")),
    "r35_schema_meta": frozenset(("name", "value")),
}

@dataclass(frozen=True)
class MigrationResult:
    migrated: bool
    schema_version: str
    preserved_legacy_rows: bool
    existing_attempts: int
    existing_uncertain: int
    authority: str = "fixture_only_no_host_change"
    cutover_authorized: bool = False

@dataclass(frozen=True)
class Recovery:
    safe_to_resume: bool
    verdict: str
    requested_action: str = "none"
    changed_host: bool = False

def _columns(db: sqlite3.Connection, name: str) -> frozenset[str]:
    if name not in REQUIRED and name not in NEW and name != "r35_fixture_meta":
        raise ValueError("unreviewed_table")
    return frozenset(row[1] for row in db.execute(f'PRAGMA table_info("{name}")'))

def _fingerprint(db):
    """In-memory digest for fixture assertions, never expose private row text."""
    rows = []
    for table, fields in (
        ("publish_jobs", "run_id,approval_sha256,post_id,draft_comment,mode,state,"
                         "created_at,attempted_at,comment_id,updated_at"),
        ("decisions", "run_id,draft_sha256,status,decided_at"),
        ("publish_settings", "name,value")):
        rows.append((table, db.execute(
            f"SELECT {fields} FROM {table} ORDER BY 1").fetchall()))
    return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()

def _attempt_counts(db):
    attempted = db.execute("SELECT COUNT(*) FROM publish_jobs "
                           "WHERE attempted_at IS NOT NULL").fetchone()[0]
    uncertain = db.execute("SELECT COUNT(*) FROM publish_jobs WHERE "
                           "state IN ('sending','uncertain','verifying',"
                           "'verified_unconfirmed','awaiting_verification',"
                           "'verification_expired')").fetchone()[0]
    return attempted, uncertain

class MigrationFixture:
    """Only a pre-existing private synthetic queue with a matching marker."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _connect(self):
        p = self.path
        if p.name != FILENAME or p.parent.name != FOLDER:
            raise ValueError("not_an_r35_fixture")
        if p.is_symlink() or p.parent.is_symlink() or not p.is_file() or not p.parent.is_dir():
            raise ValueError("unsafe_r35_fixture")
        if p.stat().st_mode & 0o077 or p.parent.stat().st_mode & 0o077:
            raise ValueError("nonprivate_r35_fixture")
        db = sqlite3.connect(p.absolute().as_uri() + "?mode=rw", uri=True,
                             isolation_level=None, timeout=4)
        try:
            db.execute("PRAGMA busy_timeout=4000")
            db.execute("BEGIN IMMEDIATE")
            marker = db.execute(
                "SELECT value FROM r35_fixture_meta WHERE name='contract'").fetchone()
            if marker != (MARKER,):
                raise ValueError("invalid_r35_marker")
            for name, required in REQUIRED.items():
                if not required.issubset(_columns(db, name)):
                    raise ValueError("legacy_queue_schema_drift")
            return db
        except BaseException:
            db.rollback()
            db.close()
            raise

    def migrate(self, *, inject_crash: bool = False) -> MigrationResult:
        """DDL and schema marker are one SQLite transaction, safe to retry."""
        db = self._connect()
        try:
            previous = _fingerprint(db)
            old_attempts, old_uncertain = _attempt_counts(db)
            db.execute("""CREATE TABLE IF NOT EXISTS r3_proposals (
                source_run TEXT PRIMARY KEY,post_id TEXT NOT NULL UNIQUE,
                draft_comment TEXT NOT NULL,seal_sha256 TEXT NOT NULL,
                fingerprint TEXT NOT NULL,snapshot_sha256 TEXT NOT NULL,
                state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS r3_owner_approvals (
                source_run TEXT PRIMARY KEY,seal_sha256 TEXT NOT NULL,
                decision TEXT NOT NULL,at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS r3_lab_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,source_run TEXT NOT NULL,
                event TEXT NOT NULL,reason TEXT NOT NULL,at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS r35_schema_meta (
                name TEXT PRIMARY KEY,value TEXT NOT NULL)""")
            for name, required in NEW.items():
                if not required.issubset(_columns(db, name)):
                    raise ValueError("r35_additive_schema_drift")
            row = db.execute(
                "SELECT value FROM r35_schema_meta WHERE name='version'").fetchone()
            if row is not None and row != (SCHEMA,):
                raise ValueError("unknown_r35_schema")
            db.execute("INSERT OR IGNORE INTO r35_schema_meta VALUES('version',?)",
                       (SCHEMA,))
            if inject_crash:
                raise RuntimeError("synthetic_power_loss_after_ddl")
            if _fingerprint(db) != previous or _attempt_counts(db) != (old_attempts,old_uncertain):
                raise AssertionError("legacy_history_mutated_during_migration")
            db.commit()
            return MigrationResult(
                migrated=True, schema_version=SCHEMA,
                preserved_legacy_rows=True, existing_attempts=old_attempts,
                existing_uncertain=old_uncertain)
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def history_summary(self):
        """Read only aggregate history, never restore a snapshot over new rows."""
        db = self._connect()
        try:
            counts = _attempt_counts(db)
            digest = _fingerprint(db)
            db.commit()
            return counts, digest
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

def reboot_reconcile(previous: CutoverState, *, legacy_timer: bool,
                     candidate_timer: bool, legacy_worker: bool,
                     candidate_worker: bool, startup_reconcile_verified: bool
                     ) -> Recovery:
    """Evaluate a synthetic boot snapshot, never operate real systemd units.

    A candidate owner after a reboot is NOT presumed to have durable consent.
    Unknown or overlapping ownership requires manual inspection; no auto-post.
    """
    if not isinstance(previous, CutoverState) or any(type(v) is not bool for v in (
        legacy_timer, candidate_timer, legacy_worker, candidate_worker,
        startup_reconcile_verified)):
        return Recovery(False, "invalid_restart_snapshot", "manual_review")
    if legacy_timer and candidate_timer or legacy_worker and candidate_worker:
        return Recovery(False, "overlapping_publisher_ownership", "hold_both")
    if (legacy_timer or legacy_worker) and (candidate_timer or candidate_worker):
        return Recovery(False, "split_publisher_ownership", "hold_both")
    if not startup_reconcile_verified:
        return Recovery(False, "startup_reconcile_unverified", "manual_review")
    if previous.phase == "baseline" and legacy_timer and not candidate_timer:
        return Recovery(True, "legacy_only_after_boot")
    if candidate_timer or candidate_worker:
        return Recovery(False, "candidate_requires_fresh_owner_review", "hold_candidate")
    # A quiesced or uncertain recovery must not silently turn a timer on.
    return Recovery(False, "quiesced_requires_manual_recovery", "manual_review")
