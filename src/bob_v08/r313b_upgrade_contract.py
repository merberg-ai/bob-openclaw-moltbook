"""R3.13b additive upgrade and independent owner-permission *design contract*.

NO live entrypoint. Every write function refuses any SQLite database other
than a marked, owner-private r313b disposable rehearsal file. Production R3
dispatch remains compiled Off in bob_r312_adapter; these settings cannot grant
network authorization. The future migration and dashboard action require
their own reviewed versioned release and explicit owner approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sqlite3

from .r313a_private_migration import (
    ADD_NAMES, _apply_copy_schema, _history_counts, _history_digest,
    _private, _shape, _tables,
)

LAB_DIR = "r313b-upgrade-fixtures"
LAB_FILE = "r313b-upgrade-copy.sqlite3"
LAB_MARKER = ".r313b-private-copy-only"
LAB_MARKER_VALUE = "r313b-private-copy-upgrade-contract-v1\n"
OFF_SETTINGS = {
    "r3_comment_dial": "off",
    "r3_manual_enabled": "0",
    "r3_auto_enabled": "0",
    "r3_auto_since": "",
}
OWNER_KEYS = frozenset(OFF_SETTINGS)
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
RUN_ID = re.compile(r"\d{8}T\d{6}Z\Z")


@dataclass(frozen=True)
class PermissionReview:
    category: str
    reason: str
    owner_permission_observed: bool = False
    dispatch_authorized: bool = False
    acted: bool = False


def validate_private_connection(db: sqlite3.Connection) -> None:
    """Refuse accidental migration of a host/live queue or attached DB."""
    database_rows = db.execute("PRAGMA database_list").fetchall()
    mains = [row for row in database_rows if row[1] == "main"]
    extras = [row for row in database_rows
              if row[1] != "main" and not (
                  row[1] == "temp" and not row[2])]
    # SQLite may allocate its internal in-memory temp schema during an
    # online backup; reject all user-ATTACHed database files or aliases.
    if len(mains) != 1 or extras:
        raise ValueError("unreviewed_attached_database")
    path = Path(mains[0][2])
    marker = path.parent / LAB_MARKER
    if (not path.is_absolute() or path.name != LAB_FILE
            or path.parent.name != LAB_DIR
            or not _private(path, directory=False, uid=os.geteuid())
            or not _private(path.parent, directory=True, uid=os.geteuid())
            or not _private(marker, directory=False, uid=os.geteuid())):
        raise ValueError("untrusted_private_upgrade_fixture")
    try:
        if marker.read_text(encoding="ascii") != LAB_MARKER_VALUE:
            raise ValueError("invalid_upgrade_fixture_marker")
    except (OSError, UnicodeError):
        raise ValueError("invalid_upgrade_fixture_marker") from None


def owner_controls(db: sqlite3.Connection) -> dict:
    """A future UI can show sanitized state; no inferred owner consent.

    R3.9's legacy proposed/auto dial is NOT enough for R3.13b: a
    separate r3_manual_enabled key is required for new manual comments.
    The installed dashboard does not currently write these keys.
    """
    try:
        settings = dict(db.execute(
            "SELECT name,value FROM publish_settings WHERE name IN "
            "('r3_comment_dial','r3_manual_enabled','r3_auto_enabled',"
            "'r3_auto_since','auto_enabled')"))
    except (sqlite3.Error, TypeError):
        return {"manual": "unverified", "automatic": "unverified",
                "authority": "none"}
    dial = settings.get("r3_comment_dial", "off")
    manual = settings.get("r3_manual_enabled", "0")
    auto = settings.get("r3_auto_enabled", "0")
    legacy = settings.get("auto_enabled", "0")
    since = settings.get("r3_auto_since", "")
    if dial not in ("off", "propose", "auto") or manual not in ("0", "1") or (
            auto not in ("0", "1") or legacy not in ("0", "1")):
        return {"manual": "unverified", "automatic": "unverified",
                "authority": "none"}
    # UI inspection is NOT an action and cannot authorize a POST.
    return {
        "manual": ("owner_review_required" if manual == "1" and
                   dial in ("propose", "auto") else "off"),
        "automatic": ("owner_review_required" if auto == "1" and
                      legacy == "1" and dial == "auto" and
                      isinstance(since, str) and bool(since) else "off"),
        "authority": "none",
    }


def review_permission(db: sqlite3.Connection, *, mode: str, source_run: str,
                      seal_sha256: str) -> PermissionReview:
    """Independent consent gate for a future authenticated manager/publisher.

    Exact per-draft seal + explicit owner decision is required for manual.
    Auto requires R3 opt-in AFTER the source was created as well as existing
    v0.7 auto consent; this never returns dispatch_authorized=True.
    """
    if (mode not in ("manual", "auto") or not isinstance(source_run, str)
            or not RUN_ID.fullmatch(source_run)
            or not isinstance(seal_sha256, str)
            or not SHA256.fullmatch(seal_sha256)):
        return PermissionReview("refused", "invalid_review_identity")
    summary = owner_controls(db)
    if summary[("manual" if mode == "manual" else "automatic")] != "owner_review_required":
        return PermissionReview("refused", "separate_r3_owner_permission_absent")
    try:
        if mode == "manual":
            row = db.execute(
                "SELECT seal_sha256,decision FROM r3_owner_approvals "
                "WHERE source_run=?", (source_run,)).fetchone()
            if row != (seal_sha256, "approved"):
                return PermissionReview("refused", "exact_bob_draft_approval_missing")
        else:
            row = db.execute(
                "SELECT value FROM publish_settings WHERE name='r3_auto_since'"
            ).fetchone()
            if row is None:
                return PermissionReview("refused", "r3_auto_since_missing")
            since = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
            if since.tzinfo is None or since.utcoffset() is None:
                raise ValueError("unverified_owner_clock")
            source_at = datetime.strptime(
                source_run, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            if source_at <= since.astimezone(timezone.utc):
                return PermissionReview("refused", "source_precedes_r3_opt_in")
        return PermissionReview("reviewed", "additional_publisher_gates_required",
                                owner_permission_observed=True)
    except (sqlite3.Error, TypeError, ValueError, AttributeError):
        return PermissionReview("refused", "owner_permission_unverifiable")


def upgrade_private_copy(db: sqlite3.Connection, *,
                         inject_crash: bool = False) -> dict:
    """Transactional DDL and Off keys, on exact marked private copy ONLY.

    No callable production/live migration entrypoint is provided.
    """
    validate_private_connection(db)
    if not _shape(db):
        raise ValueError("legacy_schema_unverified")
    existing = _tables(db)
    if any(name.startswith("r3_") and name not in ADD_NAMES for name in existing):
        raise ValueError("unknown_r3_schema")
    current = dict(db.execute(
        "SELECT name,value FROM publish_settings WHERE name IN "
        "('r3_comment_dial','r3_manual_enabled','r3_auto_enabled','r3_auto_since')"))
    if any(current.get(k, v) != v for k, v in OFF_SETTINGS.items()):
        # In particular, never silently clear or infer preexisting owner opt-in.
        raise ValueError("existing_r3_owner_setting_needs_review")
    before = _history_digest(db)
    counts = _history_counts(db)
    missing_keys = OWNER_KEYS - current.keys()
    db.execute("BEGIN IMMEDIATE")
    try:
        schema_added = _apply_copy_schema(db)
        for name, value in OFF_SETTINGS.items():
            db.execute("INSERT OR IGNORE INTO publish_settings(name,value) "
                       "VALUES(?,?)", (name, value))
        saved = dict(db.execute(
            "SELECT name,value FROM publish_settings WHERE name IN "
            "('r3_comment_dial','r3_manual_enabled','r3_auto_enabled','r3_auto_since')"))
        if saved != OFF_SETTINGS:
            raise ValueError("owner_default_off_not_preserved")
        if inject_crash:
            raise RuntimeError("r313b_synthetic_crash_before_commit")
        # The only change allowed to original tables is adding four Off
        # settings rows; preserve ALL previously existing rows by comparison.
        for name in missing_keys:
            db.execute("DELETE FROM publish_settings WHERE name=?", (name,))
        if _history_digest(db) != before or _history_counts(db) != counts:
            raise ValueError("legacy_history_changed")
        for name in missing_keys:
            db.execute("INSERT INTO publish_settings(name,value) VALUES(?,?)",
                       (name, OFF_SETTINGS[name]))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {
        "schema_added": schema_added,
        "default_off": True,
        "existing_legacy_rows_preserved": True,
        "historical_attempts": counts[1],
        "historical_uncertain": counts[2],
        "cutover_authorized": False,
        "network_dispatch_authorized": False,
    }


def code_only_rollback_review(db: sqlite3.Connection) -> dict:
    """Immutable verdict: keep present database, even after newer attempts."""
    validate_private_connection(db)
    counts = _history_counts(db)
    return {
        "rollback_scope": "code_and_units_only",
        "database_restore_allowed": False,
        "retained_attempts": counts[1],
        "retained_uncertain": counts[2],
        "cutover_authorized": False,
    }
