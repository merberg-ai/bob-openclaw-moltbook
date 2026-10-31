"""R3.13d owner-only controls for independently sealed Bob comments.

No Moltbook credentials, HTTP, service actions or schema DDL. This module is
used only by the authenticated, CSRF-protected Activity Manager. Existing
legacy Scout approval and auto settings never grant Bob-R3 permission.

All mutating functions assume their caller provides the *fixed* owner SQLite
connection and fixed private Scout source root, not a model-supplied path.
The installed manager wrapper must verify that boundary before calling.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import json
import re
import sqlite3

from bob_publish_common import now, event, setting, set_setting, RUN_ID, UUID

# Production default: neither auto enablement nor automatic queueing is exposed.
# A later independently reviewed owner canary release may change this.
R3_AUTO_UI_COMPILED_OFF = True

SHA = re.compile(r"[a-f0-9]{64}\Z")
SCHEMA_VERSION = "r313c-action-v1"


def trusted_manager_boundary(db: sqlite3.Connection) -> bool:
    """Require original fixed user-private queue; never accept attached DB.

    This is only for the real Activity Manager route, NOT for synthetic
    unit-test entrypoints that supply explicitly marked private fixtures.
    """
    import os
    import pwd
    import stat
    from bob_publish_common import DATA, DB
    try:
        uid = os.geteuid()
        home = Path.home()
        if uid == 0 or pwd.getpwuid(uid).pw_dir != str(home):
            return False
        for path, strict in (
            (home, False), (home/".config", False),
            (DATA, True), (DB, True),
        ):
            info = path.lstat()
            kind = stat.S_ISDIR if path != DB else stat.S_ISREG
            if (not kind(info.st_mode) or info.st_uid != uid
                    or info.st_mode & (0o077 if strict else 0o022)):
                return False
            if path == DB and info.st_nlink != 1:
                return False
        listed = db.execute("PRAGMA database_list").fetchall()
        main = [r for r in listed if r[1] == "main"]
        others = [r for r in listed if r[1] not in ("main","temp")
                  or r[1] == "temp" and bool(r[2])]
        return len(main) == 1 and not others and Path(main[0][2]) == DB
    except (OSError, ValueError, TypeError, sqlite3.Error, KeyError):
        return False


def schema_ready(db: sqlite3.Connection) -> bool:
    """Read-only additive schema validation; partial/future schema is not safe."""
    try:
        expected = {
            "r3_proposals": {"source_run","post_id","draft_comment",
                             "seal_sha256","fingerprint","snapshot_sha256",
                             "state","created_at","updated_at"},
            "r3_owner_approvals": {"source_run","seal_sha256","decision","at"},
            "r313c_action_envelopes": {"source_run","action_json",
                                      "action_sha256","seal_sha256","created_at"},
            "r313c_schema_meta": {"name","value"},
            "r3_lab_audit": {"id","source_run","event","reason","at"},
        }
        for table, columns in expected.items():
            observed = {row[1] for row in db.execute(
                "PRAGMA table_info(" + table + ")")}
            if observed != columns:
                return False
        return db.execute(
            "SELECT value FROM r313c_schema_meta WHERE name='version'"
        ).fetchone() == (SCHEMA_VERSION,)
    except sqlite3.Error:
        return False


def control_state(db: sqlite3.Connection) -> dict:
    """Never infer R3 permission from existing legacy v0.7 auto mode."""
    if not schema_ready(db):
        return {"schema":"unavailable","dial":"off","manual":False,
                "automatic":False,"legacy_auto":False,"auto_ui_locked":True}
    data = dict(db.execute(
        "SELECT name,value FROM publish_settings WHERE name IN "
        "('r3_comment_dial','r3_manual_enabled','r3_auto_enabled',"
        "'r3_auto_since','auto_enabled')"))
    dial = data.get("r3_comment_dial", "off")
    manual = data.get("r3_manual_enabled", "0")
    automatic = data.get("r3_auto_enabled", "0")
    legacy = data.get("auto_enabled", "0")
    if (dial not in ("off","propose","auto") or
            manual not in ("0","1") or automatic not in ("0","1") or
            legacy not in ("0","1")):
        return {"schema":"invalid","dial":"off","manual":False,
                "automatic":False,"legacy_auto":False,"auto_ui_locked":True}
    return {
        "schema":"ready", "dial":dial,
        "manual":manual == "1" and dial in ("propose","auto"),
        "automatic":automatic == "1" and dial == "auto" and legacy == "1"
                    and bool(data.get("r3_auto_since")) and
                    not R3_AUTO_UI_COMPILED_OFF,
        "legacy_auto":legacy == "1",
        "auto_ui_locked":R3_AUTO_UI_COMPILED_OFF,
    }


def set_owner_mode(db: sqlite3.Connection, operation: str, confirm: str) -> str:
    """Explicit authenticated UI action; no legacy switch or model authority.

    Automatic R3 activation is source-disabled until separate approved canary.
    Disabling R3 also cancels unattempted R3 jobs only, preserving all history.
    """
    if operation not in ("manual-on","manual-off","auto-on","all-off"):
        raise ValueError("unknown_r3_owner_operation")
    if not schema_ready(db):
        raise ValueError("r3_schema_not_installed")
    expected = {
        "manual-on":"ENABLE R3 MANUAL",
        "manual-off":"DISABLE R3 MANUAL",
        "auto-on":"ENABLE R3 AUTO",
        "all-off":"DISABLE R3",
    }[operation]
    if confirm != expected:
        raise ValueError("owner_confirmation_mismatch")
    if operation == "auto-on" and R3_AUTO_UI_COMPILED_OFF:
        raise ValueError("r3_automatic_publication_compiled_off")
    db.execute("BEGIN IMMEDIATE")
    try:
        state = control_state(db)
        if state["schema"] != "ready":
            raise ValueError("r3_schema_drift")
        if operation == "manual-on":
            # Auto never enabled by a manual-only operation.
            set_setting(db,"r3_comment_dial","propose")
            set_setting(db,"r3_manual_enabled","1")
            set_setting(db,"r3_auto_enabled","0")
            set_setting(db,"r3_auto_since","")
        else:
            # No queued attempt is ever rewritten if attempted_at is set.
            set_setting(db,"r3_comment_dial","off")
            set_setting(db,"r3_manual_enabled","0")
            set_setting(db,"r3_auto_enabled","0")
            set_setting(db,"r3_auto_since","")
            db.execute(
                "UPDATE publish_jobs SET state='cancelled',updated_at=? "
                "WHERE state='queued' AND attempted_at IS NULL "
                "AND run_id IN (SELECT source_run FROM r3_proposals)",
                (now(),))
            db.execute(
                "UPDATE r3_proposals SET state='cancelled',updated_at=? "
                "WHERE state='queued' AND source_run NOT IN "
                "(SELECT run_id FROM publish_jobs WHERE state='queued')",
                (now(),))
        event(db,"r3_owner_control",
              operation + " explicit_owner_ui; R3 publisher separately gated")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return operation


def _verified_proposal(db: sqlite3.Connection, source: Path, run: str):
    """Recompute the original Bob action from saved Scout, never UI text."""
    from bob_v08.r313c_candidate import _read_envelope, _source_seal
    if not isinstance(run,str) or not RUN_ID.fullmatch(run):
        raise ValueError("invalid_r3_run")
    action = _read_envelope(db, run)
    obs, pin, seal, fingerprint = _source_seal(db, source, action)
    row = db.execute(
        "SELECT post_id,draft_comment,seal_sha256,fingerprint,"
        "snapshot_sha256,state FROM r3_proposals WHERE source_run=?",
        (run,)).fetchone()
    if (row is None or row[:5] != (
            action.target_id, action.text, seal, fingerprint,
            pin.snapshot_sha256)):
        raise ValueError("r3_proposal_source_changed")
    return action, obs, seal, row[5]


def recent_proposals(db: sqlite3.Connection, source: Path, limit=20) -> list[dict]:
    """Bounded, verified candidates; never trust draft text in raw DB records."""
    if not schema_ready(db):
        return []
    rows = db.execute(
        "SELECT source_run FROM r3_proposals ORDER BY created_at DESC LIMIT ?",
        (min(30, max(1, int(limit))),)).fetchall()
    output = []
    for (run,) in rows:
        try:
            action, obs, seal, status = _verified_proposal(db, source, run)
            approval = db.execute(
                "SELECT seal_sha256,decision FROM r3_owner_approvals "
                "WHERE source_run=?", (run,)).fetchone()
            queued = db.execute(
                "SELECT state,mode,attempted_at,comment_id FROM publish_jobs "
                "WHERE run_id=?", (run,)).fetchone()
            output.append({
                "run":run, "post_id":action.target_id, "author":obs.author,
                "title":obs.title, "text":action.text,"reason":action.reason,
                "seal":seal,"status":status,
                "approval":approval[1] if approval and approval[0]==seal
                          else "none",
                "queue_state":queued[0] if queued else "none",
                "queue_mode":queued[1] if queued else "none",
                "attempted":bool(queued and queued[2]),
                "api_comment_id":queued[3] if queued else None,
            })
        except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
            continue
    return output


def decide_exact(db: sqlite3.Connection, source: Path,
                 run: str, seal: str, operation: str, *,
                 clock=None) -> str:
    """Manual owner decision, exact sealed Bob draft, never legacy Scout."""
    if operation not in ("approve","reject","queue"):
        raise ValueError("invalid_r3_decision")
    if not isinstance(seal,str) or not SHA.fullmatch(seal):
        raise ValueError("invalid_r3_seal")
    if not schema_ready(db):
        raise ValueError("r3_schema_not_installed")
    db.execute("BEGIN IMMEDIATE")
    try:
        owner = control_state(db)
        if operation != "reject" and not owner["manual"]:
            raise ValueError("separate_r3_manual_owner_switch_off")
        action, obs, current_seal, state = _verified_proposal(
            db, source, run)
        if seal != current_seal:
            raise ValueError("bob_draft_seal_changed")
        if db.execute("SELECT 1 FROM decisions WHERE run_id=?", (run,)).fetchone():
            raise ValueError("legacy_scout_decision_collision")
        if operation in ("approve","reject"):
            if state != "proposed":
                raise ValueError("proposal_not_in_owner_review")
            prior = db.execute(
                "SELECT decision FROM r3_owner_approvals WHERE source_run=?",
                (run,)).fetchone()
            if prior:
                raise ValueError("r3_owner_decision_already_recorded")
            db.execute(
                "INSERT INTO r3_owner_approvals "
                "(source_run,seal_sha256,decision,at) VALUES(?,?,?,?)",
                (run,seal,"approved" if operation=="approve" else "rejected",now()))
            if operation=="reject":
                db.execute("UPDATE r3_proposals SET state='rejected',"
                           "updated_at=? WHERE source_run=? AND state='proposed'",
                           (now(),run))
        else:
            if state != "proposed" or db.execute(
                "SELECT seal_sha256,decision FROM r3_owner_approvals "
                "WHERE source_run=?", (run,)).fetchone() != (seal,"approved"):
                raise ValueError("exact_bob_owner_approval_required")
            if db.execute(
                "SELECT 1 FROM publish_jobs WHERE run_id=? OR post_id=?",
                (run,action.target_id)).fetchone():
                raise ValueError("duplicate_or_existing_target")
            from datetime import datetime
            created = datetime.strptime(run,"%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc)
            at = datetime.now(timezone.utc) if clock is None else clock()
            if not isinstance(at,datetime) or at.tzinfo is None:
                raise ValueError("invalid_owner_clock")
            at = at.astimezone(timezone.utc)
            if created > at or at - created > timedelta(days=7):
                raise ValueError("manual_source_expired")
            # Publisher redoes source, queue priority, pause and rate checks
            # just before any durable attempt. This only creates a queue row.
            row=db.execute(
                "INSERT INTO publish_jobs "
                "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                "created_at,updated_at) VALUES(?,?,?,?,?,'queued',?,?)",
                (run,seal,action.target_id,action.text,"manual",
                 now(),now()))
            if db.execute(
                "UPDATE r3_proposals SET state='queued',updated_at=? "
                "WHERE source_run=? AND state='proposed'",
                (now(),run)).rowcount != 1:
                raise ValueError("proposal_concurrent_update")
        event(db,"r3_owner_review",
              run + " " + operation + " exact sealed Bob draft, no send")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return operation
