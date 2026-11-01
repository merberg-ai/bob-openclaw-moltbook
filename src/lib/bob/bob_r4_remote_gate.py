"""R4 remote identity and source preflight. Never owns an HTTP transport.

The existing Bob publisher alone may eventually supply its fixed-host
api() and credential_loader(). This module has no key, environment lookup,
urllib calls, queue mutations or side effects. Imported model/post data is
always evidence, never authority. Every failed/ambiguous read fails closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timedelta,timezone

from bob_publish_common import UUID
from bob_v08.r39_publisher_review import public_get_post,RemoteReview

MAX_PREFLIGHT=timedelta(seconds=90)


@dataclass(frozen=True)
class RemoteIdentity:
    verified:bool
    name:str=""
    reason:str="identity_unavailable"


@dataclass(frozen=True)
class PostIdentity:
    verified:bool
    reason:str


@dataclass(frozen=True)
class Preflight:
    verified:bool
    reason:str
    run:str=""
    target:str=""
    observed_author:str=""
    own_agent:str=""
    checked_at:datetime|None=None
    dispatch_authorized:bool=False


def agent_identity(payload)->RemoteIdentity:
    """Require an authenticated and explicitly successful /agents/me.

    No fallback to the locally saved Friends label, cached screen name or
    model statement, and no extraction of arbitrary nested user content.
    """
    if type(payload) is not dict or payload.get("success") is not True:
        return RemoteIdentity(False,reason="self_profile_not_authenticated")
    envelope=payload.get("data",payload)
    if type(envelope) is not dict:
        return RemoteIdentity(False,reason="self_profile_invalid")
    profile=envelope.get("agent")
    if type(profile) is not dict:
        return RemoteIdentity(False,reason="self_profile_missing_agent")
    name=profile.get("name")
    if (type(name) is not str or not 2<=len(name)<=40
            or not name[0].isalpha()
            or any(not(x.isascii() and (x.isalnum() or x in "._-"))
                   for x in name)):
        return RemoteIdentity(False,reason="self_profile_invalid_name")
    return RemoteIdentity(True,name,"authenticated_self_identity")


def verify_post(post_id:str,author:str,*,get_post=public_get_post)->PostIdentity:
    """Use the established R3 fixed-host bounded no-redirect public GET."""
    if (type(post_id) is not str or not UUID.fullmatch(post_id)
            or type(author) is not str or not author or len(author)>80
            or not callable(get_post)):
        return PostIdentity(False,"untrusted_post_identity")
    try:
        data=get_post(post_id,author)
        if type(data) is not RemoteReview or data.matched is not True:
            return PostIdentity(False,"remote_post_not_verified")
        if data.reason!="target_and_author_match":
            return PostIdentity(False,"remote_author_match_unverified")
        return PostIdentity(True,"exact_post_and_author_verified")
    except Exception:
        return PostIdentity(False,"remote_post_get_failed")


def preflight(db,source_dir,*,run:str,seal:str,at:datetime,
              post_get=public_get_post,self_get):
    """Read only, expected R4 owner and source; never reserves or POSTs."""
    from bob_r4_outbox import _head
    from bob_r4_ledger import _checked
    from bob_r4_controls import pause_state,read_modes
    try:
        if type(at) is not datetime or at.tzinfo is None:
            raise ValueError("invalid_clock")
        if not isinstance(run,str) or not isinstance(seal,str):
            raise ValueError("invalid_queued_selection")
        head=_head(db)
        if head is None or head[:3]!=(run,seal,"upvote"):
            raise ValueError("queue_changed")
        obs,decision,current,state,_=_checked(
            db,source_dir,run,allow_expired=False,at=at)
        if (seal!=current or state!="approved"
                or decision.kind!="upvote"
                or decision.target_id!=obs.post_id or
                pause_state(db) or
                read_modes(db)["upvote"]!="propose"):
            raise ValueError("source_owner_or_queue_invalid")
        if not callable(self_get):
            raise ValueError("self_profile_transport_missing")
        post_result=verify_post(obs.post_id,obs.author,get_post=post_get)
        if not post_result.verified:
            return Preflight(False,post_result.reason)
        # The existing credentialed publisher must own this authenticated
        # GET callback; no identity may be injected from an owner nickname.
        identity=agent_identity(self_get())
        if not identity.verified:
            return Preflight(False,identity.reason)
        if obs.author.casefold()==identity.name.casefold():
            return Preflight(False,"self_interaction_refused")
        return Preflight(True,"owner_source_remote_target_and_self_verified",
                         run,obs.post_id,obs.author,identity.name,
                         at.astimezone(timezone.utc))
    except Exception:
        return Preflight(False,"preflight_local_or_remote_refused")


def freshness(proof:Preflight,*,at:datetime)->bool:
    if (type(proof) is not Preflight or not proof.verified
            or type(at) is not datetime or at.tzinfo is None
            or type(proof.checked_at) is not datetime):
        return False
    elapsed=at.astimezone(timezone.utc)-proof.checked_at
    return timedelta(0)<=elapsed<=MAX_PREFLIGHT


def upvote_ack(payload)->bool:
    """Only an explicit platform success is an API ACK, not a public receipt."""
    return (type(payload) is dict and payload.get("success") is True
            and not payload.get("error"))
