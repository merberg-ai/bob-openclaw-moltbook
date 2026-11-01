"""Candidate-only R4 additive schema migration gate, NOT an installer.

No import-time writes, no dashboard-GET writes. Real deployment still requires
the signed updater's verified host identity, preflight, SQLite backup and
rollback journal before invoking the migration in one integrated release.
This module's flags are *advisory preconditions*, not authentication tokens.
"""
from __future__ import annotations

import sqlite3

from bob_r4_ledger import initialize as initialize_social
from bob_r4_ledger import schema_ready as social_ready
from bob_r4_suggestions import initialize as initialize_evidence
from bob_r4_suggestions import schema_ready as evidence_ready
from bob_r4_outbox import initialize as initialize_outbox
from bob_r4_outbox import schema_ready as outbox_ready

VERSION="r4-autonomy1-private-v1"
RELEASE="v0.8.0-autonomy1"
TABLES=frozenset((
    "r4_social_decisions","r4_social_reviews","r4_social_events",
    "r4_evidence_suggestions","r4_evidence_reviews","r4_schema_meta",
    "r4_action_outbox","r4_action_events"))
INSTALL_HOOK_COMPILED_OFF=True


def inspect(db:sqlite3.Connection) -> str:
    """Missing / complete / partial, with no CREATE or changes to main DB."""
    try:
        names={row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name LIKE 'r4_%'").fetchall()}
        if names-TABLES:
            return "partial_or_untrusted"
        have=TABLES & names
        if not have:
            return "missing"
        if (have!=TABLES or not social_ready(db) or not evidence_ready(db)
                or not outbox_ready(db)):
            return "partial_or_untrusted"
        cols={row[1] for row in db.execute(
            "PRAGMA table_info(r4_schema_meta)")}
        if cols!={"name","value"}:
            return "partial_or_untrusted"
        value=db.execute(
            "SELECT value FROM r4_schema_meta WHERE name='version'").fetchone()
        return "ready" if value==(VERSION,) else "partial_or_untrusted"
    except sqlite3.Error:
        return "partial_or_untrusted"


def migrate_candidate(db:sqlite3.Connection,*,trusted_owner:bool,
                      backup_verified:bool,installed_release:str) -> str:
    """Transactional synthetic rehearsal. Not wired into the live updater."""
    if (INSTALL_HOOK_COMPILED_OFF or trusted_owner is not True or
            backup_verified is not True or installed_release!=RELEASE):
        raise ValueError("r4_migration_not_authorized_for_install")
    db.execute("BEGIN IMMEDIATE")
    try:
        state=inspect(db)
        if state=="partial_or_untrusted":
            raise ValueError("r4_partial_schema_needs_human_review")
        if state=="missing":
            initialize_social(db)
            initialize_evidence(db)
            initialize_outbox(db)
            db.execute("CREATE TABLE r4_schema_meta("
                       "name TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO r4_schema_meta(name,value) VALUES(?,?)",
                       ("version",VERSION))
        if inspect(db)!="ready":
            raise ValueError("r4_postmigration_schema_unverified")
        db.commit()
        return "ready"
    except BaseException:
        db.rollback()
        raise


def rehearsal(db:sqlite3.Connection) -> str:
    """Explicit offline synthetic rehearsal, never a production migration."""
    if inspect(db) not in ("missing","ready"):
        raise ValueError("r4_existing_partial_schema_refused")
    db.execute("BEGIN IMMEDIATE")
    try:
        if inspect(db)=="missing":
            initialize_social(db)
            initialize_evidence(db)
            initialize_outbox(db)
            db.execute("CREATE TABLE r4_schema_meta("
                       "name TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO r4_schema_meta VALUES(?,?)",
                       ("version",VERSION))
        if inspect(db)!="ready":
            raise ValueError("r4_rehearsal_schema_unverified")
        db.commit()
        return "ready"
    except BaseException:
        db.rollback()
        raise
