"""R4 pure advisory policy: no IO, persistence, credentials or dispatcher.

This is the source-only foundation for the ONE R4 autonomy release. An eligible
verdict is NEVER sufficient for a Moltbook write: the versioned owner Controls,
transactional publisher reservation and final pre-POST gates remain mandatory.
Unsupported Moltbook APIs are OFF, not simulated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping
import re

ACTIONS = frozenset(("comment", "reply", "post", "upvote", "follow", "unfollow"))
MODES = frozenset(("off", "propose", "auto"))
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")


@dataclass(frozen=True)
class Intent:
    kind: str
    source_id: str
    target_id: str
    reason: str
    body: str = ""


@dataclass(frozen=True)
class Evidence:
    source_verified: bool = False
    target_verified: bool = False
    endpoint_verified: bool = False
    source_fresh: bool = False
    target_is_self: bool = False
    already_attempted: bool = False
    cooldown_clear: bool = False
    # For unfollow, this must be a separately verified *remote* following
    # relationship. A saved local friend is never proof of a platform follow.
    remote_following_verified: bool = False
    anomaly_active: bool = False


@dataclass(frozen=True)
class Controls:
    modes: Mapping[str, str] = field(default_factory=dict)
    owner_auto_opt_ins: frozenset[str] = frozenset()
    paused: bool = False
    total_attempted_today: int = 0
    total_daily_cap: int = 0
    action_attempted_today: Mapping[str, int] = field(default_factory=dict)
    action_daily_caps: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Verdict:
    status: str
    reason: str
    # This flag must ALWAYS remain False. The actual publisher alone decides
    # if a durable attempt is authorized after independent final checks.
    dispatch_authorized: bool = False


def review(intent: Intent, evidence: Evidence, controls: Controls) -> Verdict:
    """Return a local candidate classification, never an external permission."""
    def deny(code: str) -> Verdict:
        return Verdict("denied", code)

    if type(intent) is not Intent or type(evidence) is not Evidence or (
            type(controls) is not Controls):
        return deny("invalid_review_inputs")
    if intent.kind not in ACTIONS:
        return deny("unsupported_action")
    if (not isinstance(intent.source_id, str)
            or not IDENTIFIER.fullmatch(intent.source_id)
            or not isinstance(intent.target_id, str)
            or (intent.kind != "post" and
                not IDENTIFIER.fullmatch(intent.target_id))
            or (intent.kind == "post" and intent.target_id != "")
            or not isinstance(intent.reason, str)
            or not 1 <= len(intent.reason) <= 200
            or not isinstance(intent.body, str)
            or len(intent.body.encode("utf-8")) > 2000
            or (intent.kind in ("post","comment","reply")
                and not intent.body.strip())
            or (intent.kind in ("upvote","follow","unfollow")
                and intent.body)):
        return deny("invalid_action_shape")
    mode = controls.modes.get(intent.kind, "off")
    if mode not in MODES or mode == "off":
        return deny("owner_mode_off_or_invalid")
    if controls.paused:
        return deny("global_pause")
    if evidence.anomaly_active:
        return deny("anomaly_hold")
    if not evidence.endpoint_verified:
        return deny("unverified_api_endpoint")
    if not evidence.source_verified or not evidence.source_fresh:
        return deny("source_missing_or_stale")
    if intent.kind != "post" and not evidence.target_verified:
        return deny("target_unverified")
    if evidence.target_is_self:
        return deny("self_interaction")
    if evidence.already_attempted:
        return deny("duplicate_or_uncertain_attempt")
    if not evidence.cooldown_clear:
        return deny("cooldown_not_clear")
    if (intent.kind == "unfollow"
            and not evidence.remote_following_verified):
        return deny("remote_following_not_verified")
    if (type(controls.total_daily_cap) is not int
            or type(controls.total_attempted_today) is not int
            or controls.total_daily_cap <= 0
            or not 0 <= controls.total_attempted_today
                  < controls.total_daily_cap):
        return deny("global_daily_budget")
    per_cap = controls.action_daily_caps.get(intent.kind, 0)
    per_used = controls.action_attempted_today.get(intent.kind, 0)
    if (type(per_cap) is not int or type(per_used) is not int
            or per_cap <= 0 or not 0 <= per_used < per_cap):
        return deny("action_daily_budget")
    if mode == "auto":
        if intent.kind not in controls.owner_auto_opt_ins:
            return deny("explicit_auto_opt_in_absent")
        return Verdict("candidate_auto", "publisher_final_gates_required")
    return Verdict("candidate_propose", "owner_exact_review_required")
