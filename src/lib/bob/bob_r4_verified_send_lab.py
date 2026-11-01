"""R4 verified upvote pipeline, SIMULATION ONLY, not a public dispatcher.

Proves two exact source/remote/owner checks, durable attempted_at before an
injected fake POST, final private owner barrier, uncertainty and no replay.
The real publisher's R4 branch remains independently compiled OFF. This
module has no network client, credentials or automatic timer.

Only in-memory SQLite is permitted so accidental use against the real
Bob queue cannot consume a live action. A later separately reviewed signed
release must replace this safety harness with an installed-host-attested
publisher-owned implementation.
"""
from __future__ import annotations

from datetime import datetime,timezone
import sqlite3

from bob_r4_outbox import (
    _head, schema_ready, reserve_once, record_outcome, recover_uncertain,
)
from bob_r4_remote_gate import preflight,freshness,upvote_ack
from bob_r4_controls import api_contract,pause_state,read_modes
from bob_r4_ledger import _checked


def final_local_barrier(db,source_dir,intent,proof,*,at:datetime,
                        global_pause):
    """A last local owner/source/attempt check after the counted intent.

    Global pause checker is supplied only by the existing publisher in a
    future installed integration. This private simulation calls a fake.
    """
    if (type(at) is not datetime or at.tzinfo is None
            or not callable(global_pause) or type(intent) is not dict
            or not freshness(proof,at=at)):
        return False
    try:
        if global_pause():
            return False
        db.execute("BEGIN IMMEDIATE")
        run=intent["run"]
        row=db.execute(
            "SELECT decision_seal,kind,target_id,state,attempted_at "
            "FROM r4_action_outbox WHERE source_run=?",(run,)).fetchone()
        expected=(intent["seal"],"upvote",intent["target"],
                  "attempting",intent["attempted_at"])
        if row!=expected:
            raise ValueError("intent_changed")
        observed,decision,current,state,_=_checked(
            db,source_dir,run,allow_expired=False,at=at)
        if (state!="approved" or current!=intent["seal"]
                or observed.post_id!=intent["target"]
                or decision.kind!="upvote" or
                decision.target_id!=intent["target"] or
                proof.target!=intent["target"] or proof.run!=run
                or observed.author.casefold()!=proof.observed_author.casefold()
                or observed.author.casefold()==proof.own_agent.casefold()
                or pause_state(db) or
                read_modes(db)["upvote"]!="propose"):
            raise ValueError("owner_or_source_changed")
        if db.execute(
            "SELECT 1 FROM publish_jobs "
            "WHERE run_id=? OR (post_id=? AND attempted_at IS NOT NULL)"
            " LIMIT 1",(run,observed.post_id)).fetchone():
            raise ValueError("legacy_claim_after_intent")
        # The counted attempt cannot be undone, even if no bytes were sent.
        db.commit()
        return not global_pause()
    except (sqlite3.Error,ValueError,TypeError,KeyError,OSError):
        db.rollback()
        return False


def simulate_verified_attempt(db,source_dir,*,clock,post_get,self_get,
                              post_call,global_pause):
    """Strict in-memory-only fake GET->commit->GET->barrier->fake POST.

    No publicly callable helper in this module accepts or loads API keys.
    An unexpected exception from the fake POST is marked uncertain and never
    retried, even if it was a timeout before a body was acknowledged.
    """
    if not all(callable(x) for x in
               (clock,post_get,self_get,post_call,global_pause)):
        raise ValueError("r4_verified_synthetic_callbacks_required")
    mains=[row for row in db.execute("PRAGMA database_list")
           if row[1]=="main"]
    if len(mains)!=1 or mains[0][2] not in ("",":memory:"):
        raise ValueError("r4_verified_rehearsal_requires_memory_db")
    at=clock()
    if type(at) is not datetime or at.tzinfo is None:
        raise ValueError("r4_verified_rehearsal_bad_clock")
    if global_pause():
        return "held_global_pause"
    if not schema_ready(db):
        raise ValueError("r4_verified_schema_missing")
    if recover_uncertain(db,at=at):
        return "recovered_uncertain_no_replay"
    row=_head(db)
    if row is None:
        return "no_queued_r4_action"
    run,seal,kind,target=row
    if kind!="upvote":
        return "unreviewed_action_refused"
    first=preflight(db,source_dir,run=run,seal=seal,at=clock(),
                    post_get=post_get,self_get=self_get)
    if not first.verified or not freshness(first,at=clock()):
        return "remote_or_owner_preflight_refused"
    if global_pause():
        return "held_global_pause"
    try:
        intent=reserve_once(db,source_dir,at=clock())
    except (OSError,sqlite3.Error,ValueError,TypeError,KeyError):
        return "private_claim_refused_no_send"
    if intent is None:
        return "no_queued_r4_action"
    # From here onward the attempt is consumed, EVEN IF NEVER POSTED.
    try:
        second=preflight_post_intent(
            db,source_dir,intent,clock=clock,post_get=post_get,
            self_get=self_get)
        if (not second.verified or second.own_agent!=first.own_agent
                or second.target!=first.target or
                second.observed_author!=first.observed_author
                or not final_local_barrier(
                    db,source_dir,intent,second,at=clock(),
                    global_pause=global_pause)):
            return record_outcome(db,intent,acknowledged=False,at=clock())
        method,path=api_contract(intent["kind"],intent["target"])
        response=post_call(method,path)
        ack=upvote_ack(response)
    except Exception:
        ack=False
    return record_outcome(db,intent,acknowledged=ack,at=clock())


def preflight_post_intent(db,source_dir,intent,*,clock,post_get,self_get):
    """Second read-only remote GET after intent, never another DB claim."""
    from bob_r4_remote_gate import verify_post,agent_identity,Preflight
    try:
        observed,decision,current,state,_=_checked(
            db,source_dir,intent["run"],allow_expired=False,at=clock())
        if (state!="approved" or current!=intent["seal"] or
                observed.post_id!=intent["target"] or
                decision.kind!="upvote" or pause_state(db) or
                read_modes(db)["upvote"]!="propose"):
            raise ValueError("post_intent_local_changed")
        target=verify_post(observed.post_id,observed.author,get_post=post_get)
        identity=agent_identity(self_get())
        if (not target.verified or not identity.verified or
                identity.name.casefold()==observed.author.casefold()):
            raise ValueError("post_intent_remote_changed")
        t=clock()
        if type(t) is not datetime or t.tzinfo is None:
            raise ValueError("clock_untrusted")
        return Preflight(
            True,"post_intent_verified",intent["run"],observed.post_id,
            observed.author,identity.name,t.astimezone(timezone.utc))
    except (OSError,ValueError,sqlite3.Error,KeyError,TypeError):
        return Preflight(False,"post_intent_refused")
