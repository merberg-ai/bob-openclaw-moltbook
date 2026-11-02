"""R4 final source/owner barrier AFTER counted intent, BEFORE one API call.

Pure source-bound proof, no HTTP/keys/model. The existing publisher supplies
a private system pause callback and fixed-host remote GET function. The
caller is responsible for recording uncertain outcome on any refusal.
"""
from __future__ import annotations

from datetime import datetime,timezone
import sqlite3

from bob_r4_controls import pause_state,read_modes
from bob_r4_ledger import _checked
from bob_r4_remote_gate import Preflight,verify_post,agent_identity,freshness


def post_intent_remote(db,source_dir,intent,*,clock,post_get,self_get):
    """Second independent exact target/authenticated identity check."""
    try:
        if not all(callable(x) for x in (clock,post_get,self_get)):
            raise ValueError("untrusted_remote_callbacks")
        stamp=clock()
        if type(stamp) is not datetime or stamp.tzinfo is None:
            raise ValueError("untrusted_time")
        observed,decision,current,state,_=_checked(
            db,source_dir,intent["run"],allow_expired=False,at=stamp)
        if (state!="approved" or current!=intent["seal"] or
                observed.post_id!=intent["target"] or
                decision.kind!="upvote" or pause_state(db) or
                read_modes(db)["upvote"]!="propose"):
            raise ValueError("post_intent_local_changed")
        remote=verify_post(observed.post_id,observed.author,
                           get_post=post_get)
        me=agent_identity(self_get())
        if (not remote.verified or not me.verified
                or me.name.casefold()==observed.author.casefold()):
            raise ValueError("post_intent_remote_changed")
        stamp=clock()
        if type(stamp) is not datetime or stamp.tzinfo is None:
            raise ValueError("untrusted_clock")
        return Preflight(True,"post_intent_verified",intent["run"],
                         observed.post_id,observed.author,me.name,
                         stamp.astimezone(timezone.utc))
    except (OSError,ValueError,sqlite3.Error,KeyError,TypeError,
            RuntimeError,AttributeError):
        return Preflight(False,"post_intent_refused")


def final_local_barrier(db,source_dir,intent,proof,*,at:datetime,global_pause):
    """One final immediate local owner, seal, source and pause check."""
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
        if row!=(intent["seal"],"upvote",intent["target"],
                "attempting",intent["attempted_at"]):
            raise ValueError("intent_changed")
        observed,decision,current,state,_=_checked(
            db,source_dir,run,allow_expired=False,at=at)
        if (state!="approved" or current!=intent["seal"]
                or observed.post_id!=intent["target"] or
                decision.kind!="upvote" or
                decision.target_id!=intent["target"] or
                proof.target!=intent["target"] or proof.run!=run
                or observed.author.casefold()!=proof.observed_author.casefold()
                or observed.author.casefold()==proof.own_agent.casefold()
                or pause_state(db) or
                read_modes(db)["upvote"]!="propose"):
            raise ValueError("owner_or_source_changed")
        if db.execute(
            "SELECT 1 FROM publish_jobs WHERE run_id=? OR "
            "(post_id=? AND attempted_at IS NOT NULL) LIMIT 1",
            (run,observed.post_id)).fetchone():
            raise ValueError("legacy_claim_after_intent")
        db.commit()
        return not global_pause()
    except (sqlite3.Error,ValueError,TypeError,KeyError,OSError,RuntimeError):
        db.rollback()
        return False
