"""R4 owner policy dials: no Moltbook credentials, network, or new send path.

All action families are independently OFF by default. Propose permits only
recording *future* reviewable intent; it never queues legacy publication.
Auto is deliberately refused until the exact category has a separately
reviewed, signed, durable and verifiable worker implementation. This
prevents the user interface from making a promise the backend cannot keep.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timezone
import re
import sqlite3

ACTIONS=("comment","reply","post","upvote","follow","unfollow")
MODES=("off","propose","auto")
PREFIX="r4_mode_"
SETTING_PAUSE="r4_global_pause"
AUTO_ENGINE_COMPILED_OFF=True
CONFIRM=re.compile(r"SET R4 (COMMENT|REPLY|POST|UPVOTE|FOLLOW|UNFOLLOW) (OFF|PROPOSE|AUTO)\Z")
CAPS={"comment":2,"reply":1,"post":1,"upvote":3,"follow":1,"unfollow":0}
# Future per-action real dispatch requires its own explicit signed review.
AUTO_SHIPPED=frozenset()


def read_modes(db: sqlite3.Connection) -> dict[str,str]:
    """Strict persisted values: malformed fields are NOT silently enabled."""
    rows=dict(db.execute(
        "SELECT name,value FROM publish_settings WHERE name LIKE 'r4_mode_%'"))
    result={}
    for action in ACTIONS:
        mode=rows.get(PREFIX+action,"off")
        if type(mode) is not str or mode not in MODES:
            raise ValueError("r4_invalid_persisted_mode")
        if mode=="auto" and (AUTO_ENGINE_COMPILED_OFF or action not in AUTO_SHIPPED):
            raise ValueError("r4_auto_mode_not_currently_supported")
        result[action]=mode
    return result


def pause_state(db: sqlite3.Connection) -> bool:
    row=db.execute(
        "SELECT value FROM publish_settings WHERE name=?",
        (SETTING_PAUSE,)).fetchone()
    value=row[0] if row else "1"
    if value not in ("0","1"):
        raise ValueError("r4_invalid_pause_setting")
    return value=="1"


def set_mode(db: sqlite3.Connection, action: str, mode: str, confirmation: str,
             *, trusted: bool) -> dict:
    """Owner-initiated metadata-only transaction, never a dispatch decision."""
    if not trusted:
        raise ValueError("r4_owner_boundary_unverified")
    if action not in ACTIONS or mode not in MODES:
        raise ValueError("r4_action_or_mode_unknown")
    expected=f"SET R4 {action.upper()} {mode.upper()}"
    if type(confirmation) is not str or confirmation!=expected:
        raise ValueError("r4_confirmation_required")
    if mode=="auto" and (AUTO_ENGINE_COMPILED_OFF or action not in AUTO_SHIPPED):
        raise ValueError("r4_auto_worker_not_approved")
    db.execute("BEGIN IMMEDIATE")
    try:
        previous=read_modes(db)
        db.execute("INSERT INTO publish_settings(name,value) VALUES(?,?) "
                   "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                   (PREFIX+action,mode))
        db.execute(
            "INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
            (datetime.now(timezone.utc).isoformat(),"r4_owner_mode",
             action+":"+previous[action]+"->"+mode))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return read_modes(db)


def api_contract(action: str, target: str) -> tuple[str,str]:
    """Strict fixed-host METHOD/path contract; no user-originated URLs.

    Documented operation shape is NOT permission to call the endpoint.
    Only the existing publisher may eventually own credentials and attempts.
    """
    from urllib.parse import quote
    if action not in ACTIONS:
        raise ValueError("r4_unknown_api_action")
    if action=="post":
        if target!="":
            raise ValueError("r4_original_post_target_must_be_empty")
        return ("POST","/posts")
    if action in ("comment","reply","upvote"):
        from bob_publish_common import UUID
        if type(target) is not str or not UUID.fullmatch(target):
            raise ValueError("r4_invalid_post_id")
        return ("POST","/posts/"+target+
                ("/upvote" if action=="upvote" else "/comments"))
    if (type(target) is not str or not
            re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{1,39}",target)):
        raise ValueError("r4_invalid_agent_handle")
    return ("POST" if action=="follow" else "DELETE",
            "/agents/"+quote(target,safe="")+"/follow")
