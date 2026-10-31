"""R3.13d stage-one OFF rollout contract. Never migrates installed SQLite.

Writable functions require R3.13b's exact marker-locked disposable copy.
No network, credential, service manager, production installer or owner setter.
This adds the R3.13c action-envelope schema and exercises a trusted
source-linked proposal writer, always without queueing or dispatching.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ast
import hashlib
import os
from pathlib import Path
import sqlite3
import stat

from .core import Action
from .r3_cutover_rehearsal import verified_source
from .r3_unified import _validated
from .r313a_private_migration import (
    _history_counts, _history_digest, _private, _shape, _tables,
)
from .r313b_upgrade_contract import (
    OFF_SETTINGS, validate_private_connection, owner_controls,
)
from .r313c_candidate import ENVELOPE_DDL, canonical_action, MAX_ACTION_BYTES

SCHEMA_VERSION = "r313c-action-v1"
ENVELOPE_TABLE = "r313c_action_envelopes"
META_TABLE = "r313c_schema_meta"
ADD_TABLES = frozenset((ENVELOPE_TABLE, META_TABLE))
ENVELOPE_COLUMNS = frozenset((
    "source_run", "action_json", "action_sha256", "seal_sha256", "created_at",
))
META_COLUMNS = frozenset(("name", "value"))
INSTALLABLE = False
REAL_R3_DISPATCH = False


def _schema_shape(db: sqlite3.Connection) -> str:
    present = ADD_TABLES & _tables(db)
    if not present:
        return "absent"
    if present != ADD_TABLES:
        raise ValueError("partial_envelope_schema")
    for name, required in ((ENVELOPE_TABLE, ENVELOPE_COLUMNS),
                           (META_TABLE, META_COLUMNS)):
        actual = {row[1] for row in db.execute("PRAGMA table_info(" + name + ")")}
        if actual != required:
            raise ValueError("envelope_schema_drift")
    version = db.execute(
        "SELECT value FROM r313c_schema_meta WHERE name='version'"
    ).fetchone()
    if version != (SCHEMA_VERSION,):
        raise ValueError("unknown_envelope_schema_version")
    if db.execute("SELECT COUNT(*) FROM r313c_schema_meta").fetchone()[0] != 1:
        raise ValueError("unexpected_envelope_metadata")
    return "match"


def _off(db: sqlite3.Connection) -> bool:
    try:
        found = dict(db.execute(
            "SELECT name,value FROM publish_settings WHERE name IN "
            "('r3_comment_dial','r3_manual_enabled','r3_auto_enabled','r3_auto_since')"))
        return found == OFF_SETTINGS and owner_controls(db) == {
            "manual": "off", "automatic": "off", "authority": "none"}
    except sqlite3.Error:
        return False


def migrate_marked_copy(db: sqlite3.Connection, *,
                        inject_crash: bool = False) -> dict:
    """Transaction on disposable private-copy ONLY, after R3.13b upgrade.

    Caller must first apply upgrade_private_copy, which validates original
    legacy schema/history and creates the separate default-Off owner flags.
    No R3.13d live migration function is exposed.
    """
    validate_private_connection(db)
    if not _shape(db) or not _off(db):
        raise ValueError("unverified_private_schema_or_consent")
    if any(name.startswith("r313c_") and name not in ADD_TABLES
           for name in _tables(db)):
        raise ValueError("unexpected_r313c_table")
    state = _schema_shape(db)
    before = _history_digest(db)
    attempts = _history_counts(db)
    db.execute("BEGIN IMMEDIATE")
    try:
        if state == "absent":
            db.execute(ENVELOPE_DDL)
            db.execute("CREATE TABLE r313c_schema_meta("
                       "name TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO r313c_schema_meta VALUES('version',?)",
                       (SCHEMA_VERSION,))
        if _schema_shape(db) != "match" or not _off(db):
            raise ValueError("staging_schema_not_verified")
        if inject_crash:
            raise RuntimeError("r313d_synthetic_crash_before_commit")
        if before != _history_digest(db) or attempts != _history_counts(db):
            raise ValueError("legacy_history_modified")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {
        "envelope_schema": "match",
        "schema_added": state == "absent",
        "owner_controls": "explicit_off",
        "legacy_history_preserved": True,
        "historical_attempts": attempts[1],
        "historical_uncertain": attempts[2],
        "live_database_modified": False,
        "real_r3_dispatch": False,
        "cutover_authorized": False,
    }


def _fixed_private_source(db: sqlite3.Connection) -> Path:
    """Only the sibling scout folder of the exact verified private fixture."""
    validate_private_connection(db)
    path = Path(next(row[2] for row in db.execute("PRAGMA database_list")
                     if row[1] == "main"))
    source = path.parent.parent / "scout"
    if not _private(source, directory=True, uid=os.geteuid()):
        raise ValueError("untrusted_fixture_scout_root")
    return source


def propose_on_marked_copy(db: sqlite3.Connection, action: Action, *,
                           at: datetime) -> dict:
    """Atomic sealed Bob envelope and proposal only, on private copy.

    No publish_jobs row, owner approvals or new posting permissions.
    """
    source = _fixed_private_source(db)
    if not _off(db) or _schema_shape(db) != "match":
        raise ValueError("staged_owner_or_schema_unverified")
    observation, pin = verified_source(source, action)
    seal, fingerprint = _validated(action, observation)
    data = canonical_action(action)
    if not 0 < len(data.encode("utf-8")) <= MAX_ACTION_BYTES:
        raise ValueError("bounded_action_required")
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("timezone_aware_clock_required")
    stamp = at.astimezone(timezone.utc).isoformat()
    db.execute("BEGIN IMMEDIATE")
    try:
        current, newest_pin = verified_source(source, action, pinned=pin)
        newest_seal, newest_fingerprint = _validated(action, current)
        if (newest_pin, newest_seal, newest_fingerprint) != (
                pin, seal, fingerprint) or not _off(db):
            raise ValueError("proposal_drift_at_write")
        if db.execute(
            "SELECT 1 FROM r3_proposals WHERE source_run=? OR post_id=?",
            (action.source_run, action.target_id)).fetchone():
            raise ValueError("duplicate_source_or_target")
        if db.execute(
            "SELECT 1 FROM publish_jobs WHERE run_id=? OR post_id=?",
            (action.source_run, action.target_id)).fetchone():
            raise ValueError("already_seen_in_legacy_queue")
        db.execute(
            "INSERT INTO r313c_action_envelopes "
            "(source_run,action_json,action_sha256,seal_sha256,created_at)"
            " VALUES(?,?,?,?,?)",
            (action.source_run, data, hashlib.sha256(data.encode()).hexdigest(),
             seal, stamp))
        db.execute(
            "INSERT INTO r3_proposals "
            "(source_run,post_id,draft_comment,seal_sha256,fingerprint,"
            "snapshot_sha256,state,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,'proposed',?,?)",
            (action.source_run, action.target_id, action.text, seal,
             fingerprint, pin.snapshot_sha256, stamp, stamp))
        db.execute("INSERT INTO r3_lab_audit(source_run,event,reason,at)"
                   " VALUES(?,?,?,?)", (
                       action.source_run, "r313d_fixture_proposal",
                       "sealed_proposal_only_no_dispatch", stamp))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {
        "state": "proposed",
        "sealed": True,
        "queued": False,
        "attempted": False,
        "owner_permission_granted": False,
        "dispatch_authorized": False,
    }


def source_off_gate(root: Path) -> dict:
    """Statically inspect the reviewed checkout without running publisher.

    This is no code signing and cannot prove safety if other code is malicious.
    """
    targets = (
        ("src/bin/bob-moltbook-publisher",
         "R313C_INTEGRATION_COMPILED_OFF", True),
        ("src/lib/bob/bob_r312_adapter.py", "R312_REAL_DISPATCH", False),
        ("src/lib/bob/bob_r313c_adapter.py", "R313C_REAL_DISPATCH", False),
    )
    detail = []
    for relative, variable, required in targets:
        path = Path(root) / relative
        try:
            item = path.lstat()
            if (not stat.S_ISREG(item.st_mode) or item.st_mode & 0o022
                    or item.st_size > 512 * 1024):
                raise ValueError("unsafe_candidate_source")
            tree = ast.parse(path.read_text(encoding="utf-8"))
            values = [node.value.value for node in tree.body
                      if isinstance(node, ast.Assign)
                      and len(node.targets) == 1
                      and isinstance(node.targets[0], ast.Name)
                      and node.targets[0].id == variable
                      and isinstance(node.value, ast.Constant)]
            if values != [required]:
                raise ValueError("candidate_gate_not_off")
            detail.append("hard_off")
        except (OSError, UnicodeError, ValueError, SyntaxError):
            detail.append("unverified")
    return {
        "production_off_source": all(x == "hard_off" for x in detail),
        "gate_results": detail,
        "installable": False,
        "cutover_authorized": False,
    }
