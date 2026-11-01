"""R4 single-publisher outbox: exact owner queue, durable intent, no retries.

Source-only future release candidate. This module has NO HTTP, Moltbook key,
OpenClaw model or systemd access. It may be tested with a fake publisher
transport. Production adapter remains compiled Off, so no R4 public send is
possible from this implementation.

Initially the sole reviewed action shape is UPVOTE. Broad follow, comment,
post, reply and unfollow are deliberately not admitted. Later signed
action-specific implementations must separately prove remote identity and
receipt handling before entering the real publisher.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import hmac
import sqlite3

from bob_r4_controls import read_modes,pause_state
from bob_r4_decision import SOURCE_AGE
from bob_r4_ledger import _checked as checked_social, RUN, SHA

FORMAT="r4-single-publisher-outbox-v1"
SUPPORTED=frozenset(("upvote",))
STATES=frozenset(("queued","attempting","acknowledged","uncertain","cancelled"))
COLS=frozenset(("source_run","decision_seal","kind","target_id","state",
                "queued_at","attempted_at","updated_at","last_code"))
EVENT_COLS=frozenset(("id","source_run","kind","at"))
# Only a future, separately authorized installed version may turn the
# existing publisher's R4 adapter on. No environment/owner bit bypasses it.
PUBLIC_DISPATCH_COMPILED_OFF=True


def initialize(db:sqlite3.Connection)->None:
    """Additive, explicit install-only schema. Never invoked on page GET."""
    db.execute("""CREATE TABLE IF NOT EXISTS r4_action_outbox (
      source_run TEXT PRIMARY KEY,
      decision_seal TEXT NOT NULL,
      kind TEXT NOT NULL CHECK(kind IN ('upvote')),
      target_id TEXT NOT NULL,
      state TEXT NOT NULL CHECK(state IN
        ('queued','attempting','acknowledged','uncertain','cancelled')),
      queued_at TEXT NOT NULL,attempted_at TEXT,
      updated_at TEXT NOT NULL,last_code TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS r4_action_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_run TEXT NOT NULL,
      kind TEXT NOT NULL CHECK(kind IN
        ('owner_queued','owner_cancelled','intent_committed',
         'api_acknowledged','outcome_uncertain','recovered_uncertain')),
      at TEXT NOT NULL)""")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS r4_outbox_exact_target "
               "ON r4_action_outbox(kind,target_id)")


def schema_ready(db:sqlite3.Connection)->bool:
    try:
        for table,expected in (("r4_action_outbox",COLS),
                               ("r4_action_events",EVENT_COLS)):
            observed={r[1] for r in db.execute(
                "PRAGMA table_info("+table+")")}
            if observed!=expected:
                return False
        return True
    except sqlite3.Error:
        return False


def _utc(now:datetime)->str:
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("r4_outbox_clock_invalid")
    return now.astimezone(timezone.utc).isoformat()


def _eligible(db,source_dir,run,seal,*,at:datetime):
    """Independent exact owner approval, source freshness and policy gate."""
    if not schema_ready(db):
        raise ValueError("r4_outbox_schema_not_installed")
    obs,decision,current,state,_=checked_social(
        db,source_dir,run,allow_expired=False,at=at)
    if (not isinstance(seal,str) or not SHA.fullmatch(seal)
            or not hmac.compare_digest(current,seal)
            or state!="approved" or decision.kind not in SUPPORTED):
        raise ValueError("r4_outbox_action_or_approval_not_verified")
    if (pause_state(db) or
            read_modes(db).get(decision.kind)!="propose"):
        raise ValueError("r4_outbox_mode_paused_or_revoked")
    if decision.target_id!=obs.post_id:
        raise ValueError("r4_outbox_post_target_mismatch")
    if db.execute(
        "SELECT 1 FROM publish_jobs WHERE run_id=? OR "
        "(post_id=? AND attempted_at IS NOT NULL) LIMIT 1",
        (run,obs.post_id)).fetchone():
        raise ValueError("r4_outbox_legacy_attempt_collision")
    if db.execute(
        "SELECT 1 FROM r4_action_outbox WHERE source_run=? OR "
        "(kind=? AND target_id=?) LIMIT 1",
        (run,decision.kind,decision.target_id)).fetchone():
        raise ValueError("r4_outbox_already_queued_or_attempted")
    return decision


def queue(db,source_dir,run,seal,confirmation,*,trusted:bool,at:datetime):
    """Owner's SECOND explicit action after private R4 approval.

    Queuing records intent but is never permission for public dispatch.
    No credentials, API calls, new publisher process or timer.
    """
    if not trusted or not isinstance(run,str) or not RUN.fullmatch(run):
        raise ValueError("r4_outbox_owner_boundary_refused")
    if confirmation!="QUEUE R4 UPVOTE "+run:
        raise ValueError("r4_outbox_exact_queue_phrase_required")
    stamp=_utc(at)
    db.execute("BEGIN IMMEDIATE")
    try:
        decision=_eligible(db,source_dir,run,seal,at=at)
        db.execute(
            "INSERT INTO r4_action_outbox(source_run,decision_seal,kind,"
            "target_id,state,queued_at,attempted_at,updated_at,last_code)"
            " VALUES(?,?,?,?,'queued',?,NULL,?,'')",
            (run,seal,decision.kind,decision.target_id,stamp,stamp))
        db.execute(
            "INSERT INTO r4_action_events(source_run,kind,at) "
            "VALUES(?,'owner_queued',?)",(run,stamp))
        db.commit()
        return "queued_no_public_send"
    except BaseException:
        db.rollback()
        raise


def cancel(db,run,confirmation,*,trusted:bool,at:datetime,
           provided_seal=None):
    """Revoke only an untouched queue row. Attempting is never replayable."""
    if (not trusted or not isinstance(run,str) or not RUN.fullmatch(run)
            or confirmation!="CANCEL R4 "+run):
        raise ValueError("r4_outbox_cancel_owner_boundary_refused")
    stamp=_utc(at)
    if provided_seal is not None and (
            not isinstance(provided_seal,str) or
            not SHA.fullmatch(provided_seal)):
        raise ValueError("r4_outbox_cancel_bad_seal")
    db.execute("BEGIN IMMEDIATE")
    try:
        if provided_seal is not None:
            saved=db.execute(
                "SELECT decision_seal FROM r4_action_outbox "
                "WHERE source_run=?",(run,)).fetchone()
            if saved is None or not hmac.compare_digest(
                    saved[0],provided_seal):
                raise ValueError("r4_outbox_cancel_seal_changed")
        row=db.execute(
            "UPDATE r4_action_outbox SET state='cancelled',updated_at=?,"
            "last_code='owner_cancelled' WHERE source_run=? AND "
            "state='queued' AND attempted_at IS NULL",(stamp,run))
        if row.rowcount!=1:
            raise ValueError("r4_outbox_not_cancelable_or_already_attempted")
        db.execute(
            "INSERT INTO r4_action_events(source_run,kind,at) "
            "VALUES(?,'owner_cancelled',?)",(run,stamp))
        db.commit()
        return "cancelled"
    except BaseException:
        db.rollback()
        raise


def _head(db):
    return db.execute(
        "SELECT source_run,decision_seal,kind,target_id "
        "FROM r4_action_outbox WHERE state='queued' AND attempted_at IS NULL "
        "ORDER BY queued_at,source_run LIMIT 1").fetchone()


def reserve_once(db,source_dir,*,at:datetime):
    """Last transactional owner/source checks, BEFORE any network I/O.

    This is a pure database primitive, not a production dispatch switch.
    An 'attempting' intent is durably committed before a caller may attempt
    one fixed-target request. If the process dies, never replay it.
    """
    stamp=_utc(at)
    if not schema_ready(db):
        raise ValueError("r4_outbox_schema_not_installed")
    db.execute("BEGIN IMMEDIATE")
    try:
        head=_head(db)
        if head is None:
            db.commit()
            return None
        run,seal,kind,target=head
        # _eligible tests no existing outbox entry; perform the equivalent
        # current-source check here with this exact queued row instead.
        obs,decision,current,state,_=checked_social(
            db,source_dir,run,allow_expired=False,at=at)
        if (not hmac.compare_digest(current,seal)
                or state!="approved" or decision.kind!=kind
                or kind not in SUPPORTED or decision.target_id!=target
                or target!=obs.post_id or pause_state(db)
                or read_modes(db).get(kind)!="propose"):
            raise ValueError("r4_outbox_preintent_source_or_owner_changed")
        if db.execute(
            "SELECT 1 FROM publish_jobs WHERE run_id=? OR "
            "(post_id=? AND attempted_at IS NOT NULL) LIMIT 1",
            (run,target)).fetchone():
            raise ValueError("r4_outbox_late_legacy_collision")
        # Legacy queued publications and pending R3 are ahead of R4.
        if db.execute(
            "SELECT 1 FROM publish_jobs WHERE state='queued' LIMIT 1"
        ).fetchone():
            raise ValueError("r4_outbox_legacy_queue_has_precedence")
        count=db.execute(
            "SELECT COUNT(*) FROM r4_action_outbox WHERE attempted_at IS NOT NULL"
            " AND kind=? AND attempted_at>=?",(
                kind,at.astimezone(timezone.utc).date().isoformat())).fetchone()[0]
        from bob_r4_controls import CAPS
        if count>=CAPS[kind]:
            raise ValueError("r4_outbox_action_daily_budget")
        row=db.execute(
            "UPDATE r4_action_outbox SET state='attempting',"
            "attempted_at=?,updated_at=?,last_code='intent_committed' "
            "WHERE source_run=? AND decision_seal=? AND state='queued' "
            "AND attempted_at IS NULL",(stamp,stamp,run,seal))
        if row.rowcount!=1:
            raise ValueError("r4_outbox_concurrent_claim")
        db.execute(
            "INSERT INTO r4_action_events(source_run,kind,at) "
            "VALUES(?,'intent_committed',?)",(run,stamp))
        db.commit()
        return {"run":run,"kind":kind,"target":target,
                "seal":seal,"attempted_at":stamp,
                "publicly_verified":False}
    except BaseException:
        db.rollback()
        raise


def record_outcome(db,intent,*,acknowledged:bool,at:datetime):
    """Never treat an ACK as independently verified public visibility."""
    if type(acknowledged) is not bool or not isinstance(intent,dict):
        raise ValueError("r4_outbox_invalid_result")
    stamp=_utc(at)
    state="acknowledged" if acknowledged else "uncertain"
    kind="api_acknowledged" if acknowledged else "outcome_uncertain"
    db.execute("BEGIN IMMEDIATE")
    try:
        row=db.execute(
            "UPDATE r4_action_outbox SET state=?,updated_at=?,last_code=? "
            "WHERE source_run=? AND decision_seal=? AND state='attempting' "
            "AND attempted_at=?",
            (state,stamp,kind,intent.get("run"),intent.get("seal"),
             intent.get("attempted_at")))
        if row.rowcount!=1:
            raise ValueError("r4_outbox_result_not_current")
        db.execute(
            "INSERT INTO r4_action_events(source_run,kind,at) "
            "VALUES(?,?,?)",(intent["run"],kind,stamp))
        db.commit()
        return state
    except BaseException:
        db.rollback()
        raise


def recover_uncertain(db,*,at:datetime):
    """Crash recovery consumes old intents, never requeues them."""
    stamp=_utc(at)
    if not schema_ready(db):
        return 0
    db.execute("BEGIN IMMEDIATE")
    try:
        rows=db.execute(
            "SELECT source_run FROM r4_action_outbox WHERE "
            "state='attempting' AND attempted_at IS NOT NULL").fetchall()
        for (run,) in rows:
            db.execute(
                "UPDATE r4_action_outbox SET state='uncertain',updated_at=?,"
                "last_code='crash_or_interrupt' WHERE source_run=? "
                "AND state='attempting'",(stamp,run))
            db.execute(
                "INSERT INTO r4_action_events(source_run,kind,at) "
                "VALUES(?,'recovered_uncertain',?)",(run,stamp))
        db.commit()
        return len(rows)
    except BaseException:
        db.rollback()
        raise


def offline_rehearsal(db,source_dir,*,at:datetime,post_callback):
    """Fake transport CI only, NEVER run against real persistent Bob DB."""
    if not callable(post_callback):
        raise ValueError("r4_outbox_fake_callback_required")
    mains=[x for x in db.execute("PRAGMA database_list") if x[1]=="main"]
    if len(mains)!=1 or mains[0][2] not in ("",":memory:"):
        raise ValueError("r4_outbox_rehearsal_requires_memory_db")
    recovered=recover_uncertain(db,at=at)
    if recovered:
        return "recovered_uncertain_no_replay"
    intent=reserve_once(db,source_dir,at=at)
    if intent is None:
        return "no_queued_r4_action"
    from bob_r4_controls import api_contract
    method,path=api_contract(intent["kind"],intent["target"])
    try:
        response=post_callback(method,path)
        ack=(type(response) is dict and response.get("success") is True)
    except Exception:
        ack=False
    return record_outcome(db,intent,acknowledged=ack,at=at)
