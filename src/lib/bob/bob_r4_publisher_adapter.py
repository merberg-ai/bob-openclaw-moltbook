"""Prospective real R4 integration through Bob's EXISTING publisher only.

Public R4 writes are independently compiled OFF at the original publisher,
this adapter, and the outbox. A private approval/queue/owner mode is NOT
sufficient to arm a send. Never change these bits without a separately
reviewed installed-registry release and external acceptance.

The only eventual write shape reviewed here is a single post UPVOTE.
Follow/unfollow/reply/original posts/comments remain unsupported by this
R4 writer. Credentials and HTTPS transport remain owned exclusively by
src/bin/bob-moltbook-publisher; this adapter only accepts callbacks from
that existing worker and returns sanitized result codes.
"""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import sqlite3

R4_REAL_DISPATCH_COMPILED_OFF=True
R4_EXACT_OWNER_SEND_COMPILED_OFF=True


def _global_pause():
    path=Path.home()/".config/bob-system/paused"
    try:
        return path.is_symlink() or path.exists()
    except OSError:
        return True


def _host_verified(db)->bool:
    try:
        from bob_r4_installed_gate import verify
        from bob_r4_schema import inspect
        from bob_r313d_package import load_verified
        from bob_r313c_adapter import _trusted_single_publisher_db
        from bob_r4_outbox import PUBLIC_DISPATCH_COMPILED_OFF
        return (not PUBLIC_DISPATCH_COMPILED_OFF and verify()
                and load_verified()=="verified_registry_archive"
                and _trusted_single_publisher_db(db)
                and inspect(db)=="ready")
    except (OSError,ValueError,sqlite3.Error,KeyError,TypeError,
            ImportError,RuntimeError):
        return False


def _send_step(db,*,api_call,credential_loader,clock,
               public_get,global_pause):
    """Publisher-owned transport only; everything else source/read checked.

    No network attempt takes place until AFTER a committed attempting row.
    A host crash after that row is treated as uncertain, never queued again.
    """
    from bob_r4_outbox import (
        schema_ready,_head,reserve_once,record_outcome,recover_uncertain,
    )
    from bob_r4_remote_gate import preflight,freshness,upvote_ack
    from bob_r4_final_gate import post_intent_remote,final_local_barrier
    from bob_r4_controls import api_contract
    from bob_publish_common import DATA

    if not all(callable(x) for x in
               (api_call,credential_loader,clock,public_get,global_pause)):
        return "R4 refused: invalid trusted publisher callbacks"
    if not schema_ready(db):
        return "R4 refused: additive outbox unavailable"
    at=clock()
    if type(at) is not datetime or at.tzinfo is None or global_pause():
        return "R4 held: clock or global pause"
    if recover_uncertain(db,at=at):
        return "R4 recovered uncertain: no replay"
    head=_head(db)
    if head is None:
        return None
    run,seal,kind,target=head
    if kind!="upvote":
        return "R4 held: unreviewed action kind"
    # Authenticated self GET is passed only from THIS original publisher.
    def get_self():
        return api_call("GET","/agents/me",key=credential_loader())
    first=preflight(
        db,DATA,run=run,seal=seal,at=clock(),
        post_get=public_get,self_get=get_self)
    if not first.verified or not freshness(first,at=clock()):
        return "R4 held: exact remote/self preflight refused"
    if global_pause():
        return "R4 held: global pause"
    try:
        intent=reserve_once(db,DATA,at=clock())
    except (OSError,ValueError,sqlite3.Error,TypeError,KeyError):
        return "R4 held: private counted claim refused"
    if intent is None:
        return None
    # All paths after counted intent must end in ACK or UNCERTAIN.
    try:
        second=post_intent_remote(
            db,DATA,intent,clock=clock,
            post_get=public_get,self_get=get_self)
        if (not second.verified or not freshness(first,at=clock())
                or second.target!=first.target
                or second.observed_author!=first.observed_author
                or second.own_agent!=first.own_agent
                or not final_local_barrier(
                    db,DATA,intent,second,at=clock(),
                    global_pause=global_pause)):
            ack=False
        else:
            method,path=api_contract("upvote",intent["target"])
            # Exactly one POST through original publisher's fixed https://
            # www.moltbook.com/api/v1 API function, no model-supplied URL.
            response=api_call(method,path,key=credential_loader())
            ack=upvote_ack(response)
    except Exception:
        ack=False
    state=record_outcome(db,intent,acknowledged=ack,at=clock())
    return ("R4 upvote: api_acknowledged_not_public_receipt" if
            state=="acknowledged" else "R4 upvote: uncertain_no_replay")


def maybe_r4_publisher_step(db,*,api_call,credential_loader):
    """No credentials/network or migrations when any hard-Off gate is set."""
    if R4_REAL_DISPATCH_COMPILED_OFF or R4_EXACT_OWNER_SEND_COMPILED_OFF:
        return None
    if not _host_verified(db):
        return "R4 refused: exact installed host/source gate"
    from bob_v08.r39_publisher_review import public_get_post
    return _send_step(db,api_call=api_call,
                      credential_loader=credential_loader,
                      clock=lambda:datetime.now(timezone.utc),
                      public_get=public_get_post,global_pause=_global_pause)
