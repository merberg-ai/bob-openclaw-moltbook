"""R4 durable, source-sealed private decisions and exact owner review.

This module NEVER imports credentials, performs HTTP, queues a publish_jobs
row, or invokes a publisher. A valid OpenClaw decision may be proposed,
skipped or owner-reviewed, but can NEVER become external dispatch authority.

New schema is additive and only created by an explicit future install
migration, not by rendering a dashboard GET. Existing R3/legacy ledgers are
unchanged. All test fixtures use isolated in-memory or temporary databases.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from bob_r4_controls import ACTIONS, read_modes, pause_state
from bob_r4_decision import Decision, parse, SOURCE_AGE

FORMAT="r4-social-decision-v1"
SHA=re.compile(r"[a-f0-9]{64}\Z")
RUN=re.compile(r"\d{8}T\d{6}Z\Z")
TERMINAL=frozenset(("approved","rejected","skipped"))
PROPOSABLE=frozenset(("comment","post","upvote","follow"))
MAX_ROWS=20
COLUMN_NAMES={
    "r4_social_decisions":{
        "source_run","source_post","observed_author","snapshot_sha256",
        "kind","target_id","decision_json","seal_sha256","state",
        "recorded_at","updated_at"},
    "r4_social_reviews":{"source_run","seal_sha256","decision","at"},
    "r4_social_events":{"id","source_run","event","at"},
}


def initialize(db: sqlite3.Connection) -> None:
    """Additive, idempotent install migration, never run on a page GET."""
    db.execute("""CREATE TABLE IF NOT EXISTS r4_social_decisions (
      source_run TEXT PRIMARY KEY,
      source_post TEXT NOT NULL,
      observed_author TEXT NOT NULL,
      snapshot_sha256 TEXT NOT NULL,
      kind TEXT NOT NULL CHECK(kind IN
        ('skip','comment','post','upvote','follow')),
      target_id TEXT NOT NULL,
      decision_json TEXT NOT NULL,
      seal_sha256 TEXT NOT NULL,
      state TEXT NOT NULL CHECK(state IN
        ('skipped','proposed','approved','rejected')),
      recorded_at TEXT NOT NULL,
      updated_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS r4_social_reviews (
      source_run TEXT PRIMARY KEY,
      seal_sha256 TEXT NOT NULL,
      decision TEXT NOT NULL CHECK(decision IN ('approved','rejected')),
      at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS r4_social_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_run TEXT NOT NULL,
      event TEXT NOT NULL CHECK(event IN
        ('bob_skip','bob_proposed','owner_approved','owner_rejected')),
      at TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS r4_social_state_idx "
               "ON r4_social_decisions(state,recorded_at)")
    # Enforce same kind + target is proposed once, even from another run.
    # Skip and original post have no remotely unique target by definition.
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS r4_social_target_idx "
               "ON r4_social_decisions(kind,target_id) "
               "WHERE kind IN ('comment','upvote','follow')")


def schema_ready(db: sqlite3.Connection) -> bool:
    try:
        for table,columns in COLUMN_NAMES.items():
            present={row[1] for row in db.execute(
                "PRAGMA table_info("+table+")")}
            if present!=columns:
                return False
        return True
    except sqlite3.Error:
        return False


def _serialize(decision: Decision) -> str:
    if type(decision) is not Decision:
        raise ValueError("r4_invalid_decision_type")
    fields=asdict(decision)
    # The immutable Decision dataclass deliberately uses `kind`, while
    # OpenClaw's exact eight-field wire contract requires `type`.
    fields["type"]=fields.pop("kind")
    return json.dumps(fields,ensure_ascii=False,
                      sort_keys=True,separators=(",",":"))


def _seal(observation, envelope: str) -> str:
    return hashlib.sha256((
        FORMAT+"\n"+observation.run_id+"\n"+
        observation.post_id+"\n"+observation.snapshot_sha256+
        "\n"+envelope).encode("utf-8")).hexdigest()


def _observed(source_dir: Path, run_id: str):
    """The only source reader: independently validate existing Scout hashes."""
    from bob_v08.evidence import read_observation
    return read_observation(source_dir,run_id)


def author_count(source_dir: Path, observed) -> int:
    """Count DISTINCT other verified Scout selections, not a model claim."""
    from bob_v08.evidence import latest_observations
    recent=latest_observations(source_dir,max_scan=100,limit=20)
    return len({row.run_id for row in recent if
                row.author==observed.author and
                row.run_id!=observed.run_id})+1


def _checked(db,source_dir,run,*,allow_expired=True,at=None):
    """Reconstruct exact envelope/source seal for a stored decision."""
    row=db.execute(
        "SELECT source_post,observed_author,snapshot_sha256,kind,target_id,"
        "decision_json,seal_sha256,state,recorded_at "
        "FROM r4_social_decisions WHERE source_run=?",(run,)).fetchone()
    if not row:
        raise ValueError("r4_unknown_source_run")
    post,author,snapshot,kind,target,raw,seal,state,recorded=row
    obs=_observed(source_dir,run)
    if (obs.post_id!=post or obs.author!=author or
            obs.snapshot_sha256!=snapshot or
            not isinstance(raw,str) or len(raw.encode("utf-8"))>8000 or
            not SHA.fullmatch(str(seal)) or _seal(obs,raw)!=seal):
        raise ValueError("r4_saved_source_or_seal_mismatch")
    try:
        created=datetime.fromisoformat(recorded)
        if created.tzinfo is None:
            raise ValueError("r4_invalid_saved_clock")
        decision=parse(raw,obs,now=created,
                       author_observations=author_count(source_dir,obs))
    except (ValueError,TypeError,OverflowError):
        raise ValueError("r4_saved_decision_invalid") from None
    if (_serialize(decision)!=raw or decision.kind!=kind or
            decision.target_id!=target or
            state not in ("skipped","proposed","approved","rejected") or
            (state=="skipped")!=(kind=="skip")):
        raise ValueError("r4_decision_record_mutated")
    if not allow_expired:
        if (at is None or at.tzinfo is None or
                at.astimezone(timezone.utc)-
                datetime.strptime(run,"%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc)>SOURCE_AGE):
            raise ValueError("r4_review_source_expired")
    review=db.execute(
        "SELECT seal_sha256,decision FROM r4_social_reviews "
        "WHERE source_run=?",(run,)).fetchone()
    expected={"approved":"approved","rejected":"rejected"}
    if (review is not None and
            (review!=(seal,state) or state not in expected) or
            review is None and state in expected):
        raise ValueError("r4_review_integrity_mismatch")
    return obs,decision,seal,state,recorded


def record(db: sqlite3.Connection, source_dir: Path, observed, decision: Decision,
           *, at: datetime) -> str:
    """Consume one genuinely source-verified Bob decision, never a send.

    Caller supplies an already parser-checked model result; validation is
    repeated here, including source contents, modes and R4 pause, and then
    inside an IMMEDIATE transaction to defeat duplicate/revoke races.
    """
    if not schema_ready(db):
        raise ValueError("r4_schema_not_installed")
    if type(at) is not datetime or at.tzinfo is None:
        raise ValueError("r4_invalid_decision_clock")
    canonical=_serialize(decision)
    initial=_observed(source_dir,decision.source_run)
    if initial!=observed:
        raise ValueError("r4_model_source_not_current")
    counted=author_count(source_dir,initial)
    validated=parse(canonical,initial,now=at,author_observations=counted)
    if validated!=decision or decision.kind not in PROPOSABLE|{"skip"}:
        raise ValueError("r4_action_not_supported")
    seal=_seal(initial,canonical)
    db.execute("BEGIN IMMEDIATE")
    try:
        if not schema_ready(db):
            raise ValueError("r4_schema_changed")
        if _observed(source_dir,decision.source_run)!=initial:
            raise ValueError("r4_source_changed_during_record")
        # A second author's post may vanish while Bob is deciding.
        # Recheck independently saved distinct author sources at commit.
        if decision.kind=="follow" and author_count(source_dir,initial)<2:
            raise ValueError("r4_repeat_author_evidence_revoked")
        modes=read_modes(db)
        if pause_state(db) or not any(
                modes[name]=="propose" for name in PROPOSABLE):
            raise ValueError("r4_decisions_paused_or_off")
        if decision.kind!="skip" and modes[decision.kind]!="propose":
            raise ValueError("r4_action_revoked")
        if db.execute(
            "SELECT 1 FROM r4_social_decisions WHERE source_run=?",
            (decision.source_run,)).fetchone():
            raise ValueError("r4_source_already_decided")
        # Never replay a source already used by historical R3/legacy action.
        for table,column in (
            ("r3_proposals","source_run"),("publish_jobs","run_id")):
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                          "AND name=?",(table,)).fetchone():
                if db.execute("SELECT 1 FROM "+table+" WHERE "+column+"=?",
                              (decision.source_run,)).fetchone():
                    raise ValueError("r4_legacy_source_already_used")
        if decision.kind=="comment":
            if db.execute(
                "SELECT 1 FROM publish_jobs WHERE post_id=? LIMIT 1",
                (initial.post_id,)).fetchone():
                raise ValueError("r4_comment_target_already_attempted")
            if db.execute(
                "SELECT 1 FROM r3_proposals WHERE post_id=? LIMIT 1",
                (initial.post_id,)).fetchone():
                raise ValueError("r4_comment_target_already_proposed_in_r3")
        stamp=at.astimezone(timezone.utc).isoformat()
        state="skipped" if decision.kind=="skip" else "proposed"
        db.execute(
            "INSERT INTO r4_social_decisions "
            "(source_run,source_post,observed_author,snapshot_sha256,kind,"
            "target_id,decision_json,seal_sha256,state,recorded_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (decision.source_run,initial.post_id,initial.author,
             initial.snapshot_sha256,decision.kind,decision.target_id,
             canonical,seal,state,stamp,stamp))
        db.execute(
            "INSERT INTO r4_social_events(source_run,event,at) VALUES(?,?,?)",
            (decision.source_run,"bob_skip" if state=="skipped"
             else "bob_proposed",stamp))
        db.commit()
        return state
    except BaseException:
        db.rollback()
        raise


def review(db: sqlite3.Connection, source_dir: Path, run: str,
           provided_seal: str, operation: str, confirmation: str,
           *, trusted: bool, at: datetime) -> str:
    """Exact owner approval/rejection. Approval NEVER queues publication."""
    if (not trusted or not isinstance(run,str) or not RUN.fullmatch(run)
            or not isinstance(provided_seal,str) or
            not SHA.fullmatch(provided_seal) or
            operation not in ("approve","reject") or
            type(at) is not datetime or at.tzinfo is None):
        raise ValueError("r4_untrusted_owner_review")
    expected=f"{operation.upper()} R4 {run}"
    if confirmation!=expected:
        raise ValueError("r4_exact_review_phrase_required")
    if not schema_ready(db):
        raise ValueError("r4_schema_not_installed")
    db.execute("BEGIN IMMEDIATE")
    try:
        obs,decision,seal,state,_=_checked(
            db,source_dir,run,allow_expired=False,at=at)
        if seal!=provided_seal or state!="proposed":
            raise ValueError("r4_review_seal_or_state_mismatch")
        if operation=="approve":
            if pause_state(db) or (
                    read_modes(db)[decision.kind]!="propose"):
                raise ValueError("r4_action_paused_or_revoked")
            # A legacy send may have appeared after Bob's private proposal.
            # An approval cannot honestly represent a still-clear target.
            if decision.kind=="comment" and db.execute(
                    "SELECT 1 FROM publish_jobs WHERE post_id=? LIMIT 1",
                    (obs.post_id,)).fetchone():
                raise ValueError("r4_target_consumed_since_proposal")
        # Recheck the source *inside* owner transaction.
        if _observed(source_dir,run)!=obs:
            raise ValueError("r4_source_changed_during_review")
        if db.execute(
            "SELECT 1 FROM r4_social_reviews WHERE source_run=?",(run,)
        ).fetchone():
            raise ValueError("r4_owner_review_already_recorded")
        stamp=at.astimezone(timezone.utc).isoformat()
        state="approved" if operation=="approve" else "rejected"
        db.execute(
            "INSERT INTO r4_social_reviews(source_run,seal_sha256,decision,at)"
            " VALUES(?,?,?,?)",(run,seal,state,stamp))
        db.execute(
            "UPDATE r4_social_decisions SET state=?,updated_at=? "
            "WHERE source_run=? AND state='proposed'",(state,stamp,run))
        db.execute(
            "INSERT INTO r4_social_events(source_run,event,at) VALUES(?,?,?)",
            (run,"owner_approved" if operation=="approve"
             else "owner_rejected",stamp))
        db.commit()
        return state
    except BaseException:
        db.rollback()
        raise


def recent(db: sqlite3.Connection, source_dir: Path, *, limit:int=12) -> list[dict]:
    """Source/approval-seal verified owner Inbox, never raw unchecked drafts."""
    if type(limit) is not int or not 1<=limit<=MAX_ROWS:
        raise ValueError("r4_invalid_recent_limit")
    if not schema_ready(db):
        return []
    rows=db.execute(
        "SELECT source_run FROM r4_social_decisions "
        "ORDER BY recorded_at DESC,source_run DESC LIMIT ?",
        (limit,)).fetchall()
    output=[]
    for (run,) in rows:
        try:
            obs,action,seal,state,recorded=_checked(db,source_dir,run)
            output.append({
                "run":run,"post_id":obs.post_id,"source_author":obs.author,
                "source_title":obs.title,
                "kind":action.kind,"target":action.target_id,
                "reason":action.reason,"body":action.text,
                "title":action.title,"submolt":action.submolt,
                "state":state,"seal":seal,
                "recorded_at":recorded,"approval_is_public_permission":False,
                "queued":False,"attempted":False})
        except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):
            continue
    return output
