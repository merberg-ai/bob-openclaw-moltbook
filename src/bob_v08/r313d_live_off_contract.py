"""R3.13d owner-authorized OFF-only live additive migration core.

THIS FILE contains reviewed SQL logic, not an installer or permission to POST.
The only production caller is scripts/r313d_live_off_migration.py, which must
independently attest the fixed host, the installed Off-first release, drained
systemd publisher, verified restore-tested private backup, and TTY confirmation.

Never restore an old database after any attempted send; rollback code/units
only. Existing source, queue and historical outcomes must remain unchanged.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import json
import sqlite3

from .r313a_private_migration import (
    _shape,_tables,_history_counts,_apply_copy_schema,LEGACY_TABLES,ADD_NAMES,
)
from .r313b_upgrade_contract import OFF_SETTINGS
from .r313c_candidate import ENVELOPE_DDL
from .r313d_staging import (
    _schema_shape,_off,ADD_TABLES,SCHEMA_VERSION,
)


def _legacy_digest_without_new_settings(db: sqlite3.Connection) -> str:
    """Hash every preexisting legacy row, excluding ONLY four additive Off keys."""
    digest=hashlib.sha256()
    for table in LEGACY_TABLES:
        digest.update(table.encode("ascii"))
        for row in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid'):
            if table=="publish_settings" and row[0] in OFF_SETTINGS:
                continue
            raw=json.dumps(row,default=str,ensure_ascii=True,
                           separators=(",",":")).encode("utf-8")
            digest.update(len(raw).to_bytes(8,"big"))
            digest.update(raw)
    return digest.hexdigest()


def inspect_live_schema(db: sqlite3.Connection) -> dict:
    """Read-only summary. Unverified owner opt-in or future schema -> REFUSE."""
    try:
        if not _shape(db) or db.execute(
                "PRAGMA quick_check(1)").fetchone()!=("ok",):
            raise ValueError("legacy_schema_unverified")
        names=_tables(db)
        if any(name.startswith("r3_") and name not in ADD_NAMES
               for name in names):
            raise ValueError("unknown_r3_additive_table")
        if any(name.startswith("r313c_") and name not in ADD_TABLES
               for name in names):
            raise ValueError("unknown_r313c_table")
        keys=dict(db.execute(
            "SELECT name,value FROM publish_settings WHERE name IN "
            "('r3_comment_dial','r3_manual_enabled','r3_auto_enabled',"
            "'r3_auto_since')"))
        if any(keys.get(k,default)!=default
               for k,default in OFF_SETTINGS.items()):
            raise ValueError("installed_r3_owner_consent_not_off")
        base=ADD_NAMES & names
        if base and base!=ADD_NAMES:
            raise ValueError("partial_r35_schema")
        if base:
            # Verify existing schema contract without permitting writes.
            from .r35_migration_lab import NEW,SCHEMA
            for table,required in NEW.items():
                observed={r[1] for r in db.execute(
                    "PRAGMA table_info("+table+")")}
                if not required.issubset(observed):
                    raise ValueError("r35_schema_drift")
            if db.execute(
                "SELECT value FROM r35_schema_meta WHERE name='version'"
            ).fetchone()!=(SCHEMA,):
                raise ValueError("r35_unknown_version")
        envelope=_schema_shape(db)
        if envelope=="match" and not base:
            raise ValueError("envelope_without_r35")
        return {
            "state":"ready" if base and envelope=="match" and
                        keys==OFF_SETTINGS else "eligible",
            "legacy":"match",
            "base":"match" if base else "absent",
            "envelope":envelope,
            "owner":"explicit_off" if keys==OFF_SETTINGS else "absent_off",
            "attempts":_history_counts(db)[1],
            "uncertain":_history_counts(db)[2],
            "cutover_authorized":False,
        }
    except (OSError,ValueError,sqlite3.Error,TypeError):
        return {
            "state":"refused","legacy":"unverified","base":"unverified",
            "envelope":"unverified","owner":"unverified",
            "attempts":None,"uncertain":None,"cutover_authorized":False,
        }


def _apply_off_transaction(db: sqlite3.Connection, *,
                           inject_crash=False) -> dict:
    """SQL substep for a previously reviewed, locked host only.

    Tests invoke this against private synthetic SQLite. The public host script
    alone may invoke it against the actual installed queue after hard gates.
    """
    review=inspect_live_schema(db)
    if review["state"]=="refused":
        raise ValueError("live_off_schema_or_consent_unverified")
    before=_legacy_digest_without_new_settings(db)
    counts=_history_counts(db)
    db.execute("BEGIN IMMEDIATE")
    try:
        _apply_copy_schema(db)
        for key,value in OFF_SETTINGS.items():
            db.execute("INSERT OR IGNORE INTO publish_settings VALUES(?,?)",
                       (key,value))
        saved=dict(db.execute(
            "SELECT name,value FROM publish_settings WHERE name IN "
            "('r3_comment_dial','r3_manual_enabled','r3_auto_enabled',"
            "'r3_auto_since')"))
        if saved!=OFF_SETTINGS:
            raise ValueError("new_owner_keys_not_exact_off")
        if _schema_shape(db)=="absent":
            db.execute(ENVELOPE_DDL)
            db.execute("CREATE TABLE r313c_schema_meta("
                       "name TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO r313c_schema_meta VALUES('version',?)",
                       (SCHEMA_VERSION,))
        if not _off(db) or _schema_shape(db)!="match":
            raise ValueError("versioned_r3_schema_incomplete")
        if (before!=_legacy_digest_without_new_settings(db)
                or counts!=_history_counts(db)):
            raise ValueError("preexisting_legacy_rows_or_attempts_changed")
        if inject_crash:
            raise RuntimeError("r313d_live_off_simulated_precommit_crash")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {
        "state":"off_schema_ready",
        "historical_attempts_preserved":counts[1],
        "historical_uncertain_preserved":counts[2],
        "default_off":True,
        "real_r3_dispatch":False,
        "live_migration_completed":True,
        "canary_authorized":False,
    }
