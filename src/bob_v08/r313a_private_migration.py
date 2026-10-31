"""R3.13a trusted installed-data boundary and PRIVATE-COPY migration rehearsal.

Never changes the installed queue, settings, service units, credentials or Scout
files. The ONLY database receiving DDL is a 0600 file in an ephemeral 0700
directory after SQLite's online backup of the fixed host queue (including WAL).
This is not a production migration API or an R3 publisher permission.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

from .r35_migration_lab import REQUIRED, NEW, SCHEMA

MAX_QUEUE_BYTES = 256 * 1024 * 1024
LEGACY_TABLES = ("decisions", "publish_settings", "publish_jobs",
                 "publish_events", "published_replies")
EXTRA_COLUMNS = {
    "publish_jobs": {"comment_id", "challenge_code", "challenge_text",
                     "challenge_expires_at", "verify_answer", "last_error"},
    "publish_events": {"id", "at", "kind", "details"},
    "published_replies": {"id", "post_id", "comment_id", "detected_at"},
}
ADD_NAMES = frozenset(NEW)
# This SQL has the exact R3.5 draft-table shape; it is applied ONLY to a
# disposable copy. Any future real migration requires a separate review.
DDL = (
    """CREATE TABLE r3_proposals (
        source_run TEXT PRIMARY KEY,post_id TEXT NOT NULL UNIQUE,
        draft_comment TEXT NOT NULL,seal_sha256 TEXT NOT NULL,
        fingerprint TEXT NOT NULL,snapshot_sha256 TEXT NOT NULL,
        state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""",
    """CREATE TABLE r3_owner_approvals (
        source_run TEXT PRIMARY KEY,seal_sha256 TEXT NOT NULL,
        decision TEXT NOT NULL,at TEXT NOT NULL)""",
    """CREATE TABLE r3_lab_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,source_run TEXT NOT NULL,
        event TEXT NOT NULL,reason TEXT NOT NULL,at TEXT NOT NULL)""",
    """CREATE TABLE r35_schema_meta (
        name TEXT PRIMARY KEY,value TEXT NOT NULL)""",
)


def _private(path: Path, *, directory: bool, uid: int) -> bool:
    """lstat only: do not follow symlinks, permit other owners or shared files."""
    try:
        s = path.lstat()
        kind = stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode)
        return (kind and s.st_uid == uid and not (s.st_mode & 0o077)
                and (directory or s.st_nlink == 1))
    except OSError:
        return False


def _tables(db: sqlite3.Connection) -> set[str]:
    return {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _shape(db: sqlite3.Connection) -> bool:
    tables = _tables(db)
    if not set(LEGACY_TABLES).issubset(tables):
        return False
    for name in LEGACY_TABLES:
        expected = set(REQUIRED.get(name, ())) | EXTRA_COLUMNS.get(name, set())
        cols = {r[1] for r in db.execute('PRAGMA table_info("' + name + '")')}
        if not expected.issubset(cols):
            return False
    return True


def _owner_settings(db: sqlite3.Connection) -> str:
    """Classify only, never export raw values or grant consent."""
    settings = dict(db.execute(
        "SELECT name,value FROM publish_settings WHERE name IN "
        "('r3_comment_dial','r3_auto_enabled','r3_auto_since')"))
    if not settings:
        return "absent_off"
    if settings.get("r3_comment_dial") == "off" and settings.get(
            "r3_auto_enabled", "0") == "0":
        return "explicit_off"
    return "present_requires_owner_review"


def inspect_boundary(*, home: Path, queue: Path, paused: Path, uid: int) -> dict:
    """Fixed-root metadata contract. CLI supplies ONLY known constants.

    Test injection is deliberately separate from the user-facing CLI. Never
    print paths, drafts, private settings or systemd command/environment text.
    """
    home = Path(home)
    queue = Path(queue)
    paused = Path(paused)
    blockers = []
    if (queue != home / ".config" / "moltbook" / "activity-queue.sqlite3"
            or paused != home / ".config" / "bob-system" / "paused"):
        blockers.append("host_paths_not_fixed")
    for path, directory, reason in (
        (home, True, "home_untrusted"),
        (home / ".config", True, "config_directory_not_private"),
        (queue.parent, True, "scout_source_directory_not_private"),
        (paused.parent, True, "pause_directory_not_private"),
        (queue, False, "queue_file_not_private"),
    ):
        # Normal Unix home may be 0755; require owner/no symlink, but
        # enforce 0700 on every directory containing Bob private data.
        if path == home:
            try:
                s = path.lstat()
                good = stat.S_ISDIR(s.st_mode) and s.st_uid == uid
            except OSError:
                good = False
        else:
            good = _private(path, directory=directory, uid=uid)
        if not good:
            blockers.append(reason)
    try:
        if queue.stat().st_size > MAX_QUEUE_BYTES:
            blockers.append("queue_too_large")
    except OSError:
        blockers.append("queue_unavailable")
    try:
        paused_state = ("untrusted" if paused.is_symlink() else
                        "paused" if paused.exists() else "not_paused")
        if paused_state == "paused" and not _private(
                paused, directory=False, uid=uid):
            paused_state = "untrusted"
    except OSError:
        paused_state = "untrusted"
    if paused_state == "untrusted":
        blockers.append("pause_marker_untrusted")
    legacy_shape = "unverified"
    additive = "unverified"
    owner_settings = "unverified"
    if not blockers:
        try:
            with sqlite3.connect(queue.absolute().as_uri() + "?mode=ro",
                                 uri=True, timeout=3) as db:
                db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN")
                legacy_shape = "match" if _shape(db) else "mismatch"
                existing = ADD_NAMES & _tables(db)
                other_r3 = {n for n in _tables(db) if n.startswith("r3_")}
                additive = ("absent" if not existing and not other_r3 else
                            "existing_needs_review")
                owner_settings = (_owner_settings(db) if legacy_shape == "match"
                                  else "unverified")
                db.rollback()
        except (OSError, sqlite3.Error, ValueError):
            blockers.append("queue_read_only_snapshot_failed")
    if legacy_shape != "match":
        blockers.append("legacy_schema_unverified")
    if additive != "absent":
        blockers.append("additive_schema_not_empty")
    return {
        "format": "bob-r313a-host-boundary-v1",
        "source_root": "fixed_existing_moltbook_data",
        "queue_file": "private" if "queue_file_not_private" not in blockers else "unverified",
        "pause": paused_state,
        "legacy_schema": legacy_shape,
        "additive_schema": additive,
        "r3_settings": owner_settings,
        "private_copy_eligible": not blockers,
        "review_blockers": sorted(set(blockers)),
        "installed_executable_integrity": "not_verified",
        "real_dispatch_enabled": False,
        "cutover_authorized": False,
        "host_changes": 0,
    }


def _history_digest(db: sqlite3.Connection) -> str:
    """Hash ALL legacy rows, including attempted/uncertain, without exporting data."""
    digest = hashlib.sha256()
    for name in LEGACY_TABLES:  # fixed identifiers, no dynamic caller names
        digest.update(name.encode("ascii"))
        for row in db.execute('SELECT * FROM "' + name + '" ORDER BY rowid'):
            digest.update(json.dumps(row, default=str, ensure_ascii=True,
                                     separators=(",", ":")).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _history_counts(db: sqlite3.Connection) -> tuple[int, int, int]:
    return (
        db.execute("SELECT COUNT(*) FROM publish_jobs").fetchone()[0],
        db.execute("SELECT COUNT(*) FROM publish_jobs "
                   "WHERE attempted_at IS NOT NULL").fetchone()[0],
        db.execute("SELECT COUNT(*) FROM publish_jobs WHERE state IN "
                   "('sending','uncertain','verifying','verified_unconfirmed',"
                   "'awaiting_verification','verification_expired',"
                   "'verification_failed')").fetchone()[0],
    )


def _apply_copy_schema(db: sqlite3.Connection) -> bool:
    """Caller MUST hold a write transaction on a disposable private copy."""
    existing = ADD_NAMES & _tables(db)
    if existing and existing != ADD_NAMES:
        raise ValueError("partial_r3_schema")
    if existing:
        for name, required in NEW.items():
            cols = {r[1] for r in db.execute('PRAGMA table_info("' + name + '")')}
            if not required.issubset(cols):
                raise ValueError("r3_schema_drift")
        version = db.execute(
            "SELECT value FROM r35_schema_meta WHERE name='version'").fetchone()
        if version != (SCHEMA,):
            raise ValueError("unknown_r3_version")
        return False
    for ddl in DDL:
        db.execute(ddl)
    db.execute("INSERT INTO r35_schema_meta(name,value) VALUES('version',?)",
               (SCHEMA,))
    return True


def _rehearse_copy(source: Path) -> dict:
    """Online SQLite backup includes committed WAL; never raw file copy."""
    with tempfile.TemporaryDirectory(prefix="bob-r313a-private-") as tmp:
        folder = Path(tmp)
        if not _private(folder, directory=True, uid=os.geteuid()):
            raise ValueError("temporary_directory_not_private")
        copied = folder / "queue-copy.sqlite3"
        fd = os.open(copied, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(source.absolute().as_uri() + "?mode=ro",
                                     uri=True, timeout=5)) as live:
            live.execute("PRAGMA query_only=ON")
            with closing(sqlite3.connect(copied, isolation_level=None,
                                         timeout=5)) as copy:
                live.backup(copy, pages=64, sleep=0.02)
                if not _shape(copy) or ADD_NAMES & _tables(copy) or any(
                        x.startswith("r3_") for x in _tables(copy)):
                    raise ValueError("copied_schema_unexpected")
                if copy.execute("PRAGMA quick_check(1)").fetchone() != ("ok",):
                    raise ValueError("copied_database_check_failed")
                before = _history_digest(copy)
                counts = _history_counts(copy)
                # Inject a crash between DDL and commit. All new tables must
                # roll back before the successful migration.
                copy.execute("BEGIN IMMEDIATE")
                try:
                    _apply_copy_schema(copy)
                    raise RuntimeError("synthetic_crash_before_commit")
                except RuntimeError:
                    copy.rollback()
                if ADD_NAMES & _tables(copy):
                    raise ValueError("copy_ddl_crash_rollback_failed")
                copy.execute("BEGIN IMMEDIATE")
                try:
                    migrated = _apply_copy_schema(copy)
                    if _history_digest(copy) != before:
                        raise ValueError("legacy_history_changed")
                    copy.commit()
                except BaseException:
                    copy.rollback()
                    raise
                copy.execute("BEGIN IMMEDIATE")
                try:
                    second = _apply_copy_schema(copy)
                    copy.commit()
                except BaseException:
                    copy.rollback()
                    raise
                if (not migrated or second or _history_digest(copy) != before
                        or _history_counts(copy) != counts):
                    raise ValueError("migration_not_idempotent_or_history_changed")
                return {
                    "format": "bob-r313a-private-migration-v1",
                    "private_copy_migrated": True,
                    "crash_rollback_pass": True,
                    "idempotent": True,
                    "full_legacy_history_preserved": True,
                    "historical_jobs": counts[0],
                    "historical_attempts": counts[1],
                    "historical_uncertain": counts[2],
                    "temporary_copy_deleted_on_return": True,
                    "live_schema_migrated": False,
                    "live_files_changed_by_rehearsal": False,
                    "external_requests": 0,
                    "cutover_authorized": False,
                }


def rehearse(*, home: Path, queue: Path, paused: Path, uid: int) -> dict:
    """Return sanitized, always non-authorizing result; never accept CLI paths."""
    review = inspect_boundary(home=home, queue=queue, paused=paused, uid=uid)
    if not review["private_copy_eligible"]:
        return {"host": review, "rehearsal": "refused_preflight",
                "cutover_authorized": False}
    try:
        outcome = _rehearse_copy(Path(queue))
    except (OSError, sqlite3.Error, ValueError, RuntimeError):
        return {"host": review, "rehearsal": "failed_closed",
                "cutover_authorized": False}
    return {"host": review, "rehearsal": outcome,
            "cutover_authorized": False}
