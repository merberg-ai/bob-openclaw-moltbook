"""R4 bounded read-only evidence projection from EXISTING Bob private ledgers.

The renderers distinguish owner notes, locally classified friends, Bob R3
proposals, attempts, API ACKs and independently observed public receipts.
Local labels are never evidence of a remote follow. This module never reads
model prompts, arbitrary Scout post text, credentials, or network resources.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from pathlib import Path
import os
import re
import sqlite3
import stat

from bob_publish_common import DB
from bob_r4_controls import ACTIONS, CAPS, read_modes, pause_state

MAX_QUEUE=12
MAX_PEOPLE=12
MAX_MEMORY=8
MAX_EVENTS=12
MAX_DB_BYTES=256*1024*1024
ALLOWED_JOB_STATES=frozenset((
    "queued","sending","uncertain","published","failed","verifying",
    "verified_unconfirmed","awaiting_verification","verification_expired",
    "verification_failed","cancelled","expired"))
RUN=re.compile(r"\d{8}T\d{6}Z\Z")
ALLOWED_EVENTS=frozenset(("r313d_skip","r313d_proposed",
    "r313c_claimed","r313c_receipt","r313c_recovered"))


def _exists(db: sqlite3.Connection, name: str) -> bool:
    return bool(db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone())


def _count(db: sqlite3.Connection, table: str, *, where: str="", args=()):
    if table not in ("publish_jobs","r3_proposals","bob_memories",
                     "bob_friends","original_posts","r3_lab_audit",
                     "r4_social_decisions"):
        raise ValueError("r4_unreviewed_table")
    if not _exists(db,table):
        return 0
    # All predicate text is authored, never supplied by the caller.
    if where not in (""," WHERE attempted_at IS NOT NULL",
                     " WHERE state='proposed'"," WHERE state='active'"):
        raise ValueError("r4_unreviewed_predicate")
    return db.execute("SELECT COUNT(*) FROM "+table+where,args).fetchone()[0]


def empty():
    return {
        "available":False,
        "publisher_jobs":0,"attempted":0,"r3_proposed_recorded":0,
        "saved_memories":0,"saved_friends":0,"originals":0,
        "r4_proposed":0,"r4_total_decisions":0,"r4_recent":[],
        "r4_suggestions":[],"r4_pending_suggestions":0,
        "recent_jobs":[],"recent_events":[],"people":[],"memory_titles":[],
        "controls":{kind:"off" for kind in ACTIONS},
        "r4_paused":True, "latest_r3_source":None,
        "publicly_verified_by_current_view":False,
        "read_only":True,
        "external_write_requests":0,
    }


def project_db(db: sqlite3.Connection) -> dict:
    """Queries known schemas only; no CREATE, INSERT, UPDATE or PRAGMA writes."""
    result=empty()
    if not _exists(db,"publish_settings") or not _exists(db,"publish_jobs"):
        return result
    result["controls"]=read_modes(db)
    result["r4_paused"]=pause_state(db)
    result["publisher_jobs"]=_count(db,"publish_jobs")
    result["attempted"]=_count(
        db,"publish_jobs",where=" WHERE attempted_at IS NOT NULL")
    result["r3_proposed_recorded"]=_count(
        db,"r3_proposals",where=" WHERE state='proposed'")
    result["saved_memories"]=_count(
        db,"bob_memories",where=" WHERE state='active'")
    result["saved_friends"]=_count(
        db,"bob_friends",where=" WHERE state='active'")
    result["originals"]=_count(db,"original_posts")
    result["r4_total_decisions"]=_count(db,"r4_social_decisions")
    if _exists(db,"r4_social_decisions"):
        from bob_r313d_package import load_verified
        if load_verified()!="verified_registry_archive":
            raise ValueError("r4_saved_source_package_untrusted")
        from bob_r4_ledger import recent,schema_ready
        if not schema_ready(db):
            raise ValueError("r4_social_schema_unverified")
        result["r4_proposed"]=db.execute(
            "SELECT COUNT(*) FROM r4_social_decisions "
            "WHERE state='proposed'").fetchone()[0]
        # Source+seal independently checked, never render unchecked DB text.
        from bob_publish_common import DATA
        result["r4_recent"]=recent(db,DATA,limit=12)
        from bob_r4_suggestions import recent as recent_suggestions
        from bob_r4_suggestions import schema_ready as suggestions_ready
        if not suggestions_ready(db):
            raise ValueError("r4_evidence_suggestion_schema_unverified")
        result["r4_suggestions"]=recent_suggestions(db,DATA,limit=12)
        result["r4_pending_suggestions"]=db.execute(
            "SELECT COUNT(*) FROM r4_evidence_suggestions "
            "WHERE state='pending'").fetchone()[0]
    recent=db.execute(
        "SELECT run_id,state,mode,attempted_at,comment_id FROM publish_jobs "
        "ORDER BY created_at DESC,run_id DESC LIMIT ?",(MAX_QUEUE,)).fetchall()
    for run,state,mode,attempted,comment in recent:
        if not isinstance(run,str) or not RUN.fullmatch(run):
            continue
        clean=state if state in ALLOWED_JOB_STATES else "unrecognized"
        result["recent_jobs"].append({
            "source_run":run,"state":clean,
            "mode":mode if mode in ("manual","auto") else "unrecognized",
            "attempt_recorded":bool(attempted),
            "api_acknowledged":clean=="published",
            # This view does NOT do external GET and must never invent it.
            "publicly_visible":"not_checked",
            "has_comment_id":bool(isinstance(comment,str) and len(comment)==36)})
    if _exists(db,"r3_lab_audit"):
        rows=db.execute(
            "SELECT source_run,event,at FROM r3_lab_audit "
            "ORDER BY id DESC LIMIT ?",(MAX_EVENTS,)).fetchall()
        for run,kind,at in rows:
            if kind not in ALLOWED_EVENTS or not isinstance(run,str) or not RUN.fullmatch(run):
                continue
            result["recent_events"].append({
                "source_run":run,"kind":kind,
                "at":at if isinstance(at,str) and len(at)<=64 else "unknown"})
        if result["recent_events"]:
            result["latest_r3_source"]=result["recent_events"][0]["source_run"]
    if _exists(db,"bob_friends"):
        rows=db.execute(
            "SELECT handle,relationship,source_kind FROM bob_friends "
            "WHERE state='active' ORDER BY updated_at DESC LIMIT ?",
            (MAX_PEOPLE,)).fetchall()
        for handle,relationship,kind in rows:
            if (isinstance(handle,str) and re.fullmatch(
                    r"[A-Za-z0-9_.-]{2,40}",handle) and
                    relationship in ("interesting","acquaintance","friend")):
                result["people"].append({
                    "handle":handle,"local_relationship":relationship,
                    "evidence":"owner_entry" if kind=="manual"
                    else "scout_snapshot" if kind=="scout_snapshot"
                    else "unverified",
                    "remote_following":"unknown"})
    if _exists(db,"bob_memories"):
        rows=db.execute(
            "SELECT title,category,confidence FROM bob_memories "
            "WHERE state='active' AND source_kind='operator' "
            "ORDER BY updated_at DESC LIMIT ?",(MAX_MEMORY,)).fetchall()
        for title,category,confidence in rows:
            if (isinstance(title,str) and 0<len(title)<=160 and
                    isinstance(category,str) and len(category)<=40):
                result["memory_titles"].append({
                    "title":title,"category":category,
                    "confidence":confidence if confidence in
                    ("low","medium","high") else "unverified",
                    "provenance":"operator_entered_not_agent_recall"})
    result["available"]=True
    return result


def snapshot(path: Path=DB) -> dict:
    """Read-only even on missing DB. Do not create a database on page load."""
    path=Path(path)
    try:
        info=path.lstat()
        if (not stat.S_ISREG(info.st_mode) or
                info.st_uid!=os.geteuid() or
                info.st_mode & 0o022 or not 0<info.st_size<=MAX_DB_BYTES):
            return empty()
        with closing(sqlite3.connect(
                path.absolute().as_uri()+"?mode=ro",uri=True,timeout=3)) as db:
            db.execute("PRAGMA query_only=ON")
            return project_db(db)
    except (sqlite3.Error,OSError,ValueError,TypeError,KeyError,
            ImportError,AttributeError):
        return empty()
