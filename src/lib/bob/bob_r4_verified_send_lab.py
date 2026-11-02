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
from bob_r4_controls import api_contract
from bob_r4_final_gate import (
    final_local_barrier,post_intent_remote as preflight_post_intent
)


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
        if (not second.verified or not freshness(first,at=clock())
                or second.own_agent!=first.own_agent
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


