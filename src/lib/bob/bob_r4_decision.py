"""R4 strict Bob-agent social decision parser, proposal-only and no I/O.

The input observation MUST come from the existing sealed Scout reader. Even a
valid action creates NO approval, queue or API permission. A model may only
target the precise saved post or its observed author; no arbitrary handles,
URLs, submolts or unseen reply parent can be supplied by model text.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import json
import re

from bob_r4_controls import ACTIONS

FIELDS=frozenset((
    "type","source_run","target_id","reason","text",
    "title","submolt","parent_id"))
RUN=re.compile(r"\d{8}T\d{6}Z\Z")
HANDLE=re.compile(r"[A-Za-z][A-Za-z0-9_.-]{1,39}\Z")
SOURCE_AGE=timedelta(hours=48)
MAX_OUTPUT=8000


@dataclass(frozen=True)
class Decision:
    kind:str
    source_run:str
    target_id:str
    reason:str
    text:str
    title:str
    submolt:str
    parent_id:str


def parse(raw:str, observed, *, now:datetime,
          author_observations:int=1) -> Decision:
    """Fail closed on missing keys, invalid targets, stale evidence or prose."""
    if (type(raw) is not str or not 0<len(raw.encode("utf-8"))<=MAX_OUTPUT
            or type(now) is not datetime or now.tzinfo is None):
        raise ValueError("r4_untrusted_decision_envelope")
    try:
        obj=json.loads(raw)
    except (TypeError,ValueError,json.JSONDecodeError):
        raise ValueError("r4_invalid_decision_json") from None
    if not isinstance(obj,dict) or set(obj)!=FIELDS or any(
            type(v) is not str for v in obj.values()):
        raise ValueError("r4_invalid_exact_eight_field_schema")
    kind=obj["type"]
    if kind not in set(ACTIONS) | {"skip"}:
        raise ValueError("r4_unknown_action_type")
    source=getattr(observed,"run_id",None)
    post=getattr(observed,"post_id",None)
    author=getattr(observed,"author",None)
    if not isinstance(source,str) or not RUN.fullmatch(source):
        raise ValueError("r4_unverified_source_shape")
    try:
        created=datetime.strptime(source,"%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc)
        stamp=now.astimezone(timezone.utc)
    except (ValueError,TypeError,OverflowError):
        raise ValueError("r4_invalid_source_time") from None
    if stamp<created or stamp-created>SOURCE_AGE:
        raise ValueError("r4_stale_source")
    if obj["source_run"]!=source:
        raise ValueError("r4_changed_source_id")
    if not isinstance(post,str) or not re.fullmatch(
            r"[a-fA-F0-9]{8}-(?:[a-fA-F0-9]{4}-){3}[a-fA-F0-9]{12}",post):
        raise ValueError("r4_invalid_saved_post_id")
    if kind=="skip":
        if (obj["target_id"]!=post or obj["text"] or obj["title"]
                or obj["submolt"] or obj["parent_id"]):
            raise ValueError("r4_invalid_skip_fields")
        if len(obj["reason"])>200:
            raise ValueError("r4_skip_reason_too_long")
    else:
        reason=obj["reason"]
        if (not reason.strip() or len(reason)>200
                or any(ord(c)<32 and c not in "\n\t" for c in reason)):
            raise ValueError("r4_invalid_reason")
        if kind in ("comment","reply","upvote"):
            if obj["target_id"]!=post:
                raise ValueError("r4_model_changed_post_target")
        elif kind in ("follow","unfollow"):
            if (not isinstance(author,str) or not HANDLE.fullmatch(author)
                    or obj["target_id"]!=author):
                raise ValueError("r4_model_changed_verified_author")
        elif kind=="post" and obj["target_id"]!="":
            raise ValueError("r4_model_original_target_invalid")
        if kind in ("comment","reply","post"):
            text=obj["text"]
            if (not text.strip() or len(text.encode("utf-8"))>1800
                    or len(text.split())>300 or "\x00" in text):
                raise ValueError("r4_invalid_draft_body")
        elif obj["text"]:
            raise ValueError("r4_noncontent_action_has_body")
        if kind=="post":
            if (obj["submolt"]!="general" or
                    not 1<=len(obj["title"].strip())<=120):
                raise ValueError("r4_original_post_unreviewed_destination")
        elif obj["title"] or obj["submolt"]:
            raise ValueError("r4_nonpost_metadata_forbidden")
        # Scout feed contains a selected post but does NOT verify any parent
        # comment ID, so replies are not admitted for R4 publication yet.
        if kind=="reply" or obj["parent_id"]:
            raise ValueError("r4_reply_parent_not_independently_verified")
        # Local observations prove a saved source, but NOT platform following.
        # Unfollow stays blocked until a fresh remote graph is available.
        if kind=="unfollow":
            raise ValueError("r4_remote_following_not_verified")
        # Follow deliberately requires at least two separate sealed Scout
        # observations of the same author, not one flattering post.
        if (kind=="follow" and
                (type(author_observations) is not int or author_observations<2)):
            raise ValueError("r4_insufficient_repeat_author_evidence")
    return Decision(kind,source,obj["target_id"],obj["reason"],
                    obj["text"],obj["title"],obj["submolt"],obj["parent_id"])


def exact_example(observed) -> str:
    """Trusted JSON schema example outside untrusted Scout post material."""
    return json.dumps({
        "type":"skip","source_run":observed.run_id,
        "target_id":observed.post_id,
        "reason":"","text":"","title":"","submolt":"","parent_id":""
    },sort_keys=True,separators=(",",":"))
