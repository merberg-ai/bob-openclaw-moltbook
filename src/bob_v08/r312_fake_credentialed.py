"""R3.12 fake-credentialed POST inside ONE legacy publisher executable.

Never a live client. Only explicit inert CLI and a private marker-locked
synthetic R3.3 queue may call this harness. The fake key intentionally is
NOT a Moltbook API key, and the transport rejects all other keys.
No hostname, sockets, urllib, credentials files, or system services.

The real publisher's ordinary R3 path is compiled Off. A real activation
needs a distinct reviewed release, authenticated transport and owner opt-in.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .r311_inert_entry import _load_marked_input, _synthetic_clock
from .r310_atomic_claim_lab import rehearse_atomic_claim
from .r39_publisher_review import RemoteReview
from .r38_dispatch_lab import (
    SimulatedPowerLoss, _barrier, _settle,
)

FAKE_KEY = "R312_SYNTHETIC_CREDENTIAL_NO_NETWORK"
COMMENT_ID = "11111111-1111-4111-8111-111111111111"


@dataclass(frozen=True)
class FakeResult:
    state: str
    reason: str
    attempted: bool = False
    post_calls: int = 0
    simulated: bool = True
    acted: bool = False
    dispatch_authorized: bool = False


class FakeCredentialedTransport:
    """A fake in-memory API surface; exact type required by the rehearsal."""

    def __init__(self, response="ack"):
        if response not in ("ack", "timeout", "malformed", "challenge", "rejected"):
            raise ValueError("invalid_fake_response")
        self.response = response
        self.calls = []

    def post(self, *, method: str, path: str, payload: dict, key: str,
             target: str):
        if (method != "POST" or path != "/posts/" + target + "/comments"
                or key != FAKE_KEY or not isinstance(payload, dict)
                or set(payload) != {"content"}
                or not isinstance(payload["content"], str)
                or not payload["content"]):
            raise ValueError("fake_request_not_exact")
        self.calls.append(hashlib.sha256(
            (target + "\n" + payload["content"]).encode("utf-8")).hexdigest())
        if self.response == "timeout":
            raise TimeoutError("fake_network_unknown")
        if self.response == "rejected":
            return {"success": False}
        if self.response == "malformed":
            return {"success": True}
        if self.response == "challenge":
            return {"success": True, "verification_required": True}
        return {"success": True, "comment": {"id": COMMENT_ID}}


def run_fake_credentialed(path: Path, *, response="ack",
                          failpoint="", after_intent=None) -> FakeResult:
    """Simulate final pre-POST path with fake auth and fake response only.

    There is no path to this from the default publisher timer/manager.
    R3.9 + R3.10 verify and count an intent before even the FAKE POST.
    The R3.8 final barrier is repeated before fake transport to detect
    source, owner, saved-friend, budget or pause drift after the claim.
    """
    if response not in ("ack", "timeout", "malformed", "challenge", "rejected"):
        return FakeResult("refused", "invalid_fake_response")
    if failpoint not in ("", "after_intent", "after_post"):
        return FakeResult("refused", "invalid_fake_failpoint")
    try:
        lab, action, mode, author = _load_marked_input(Path(path))
        instant = _synthetic_clock(action)
    except (OSError, ValueError, TypeError):
        return FakeResult("refused", "invalid_private_inert_fixture")

    fake_get = lambda pid, expected: RemoteReview(
        pid == action.target_id and expected.casefold() == author.casefold(),
        "synthetic_id_and_author_match")
    claimed = rehearse_atomic_claim(
        lab, action, mode=mode,
        clock=lambda: instant, public_get=fake_get)
    if claimed.state != "claimed_simulated":
        return FakeResult("refused", claimed.reason,
                          attempted=claimed.attempted_at_recorded)
    if failpoint == "after_intent":
        raise SimulatedPowerLoss("synthetic_crash_after_committed_attempt")
    if after_intent is not None:
        after_intent()
    barrier = _barrier(
        lab, lab.path.parent.parent / "scout", action, mode,
        lab.path.parent.parent / "paused", instant)
    if barrier != "clear":
        lab.simulated_uncertain(action.source_run, at=instant)
        return FakeResult("uncertain_simulated", "barrier_" + barrier,
                          attempted=True)

    fake = FakeCredentialedTransport(response)
    try:
        reply = fake.post(
            method="POST", path="/posts/" + action.target_id + "/comments",
            payload={"content": action.text}, key=FAKE_KEY,
            target=action.target_id)
    except Exception:
        lab.simulated_uncertain(action.source_run, at=instant)
        return FakeResult("uncertain_simulated", "fake_post_unknown",
                          attempted=True, post_calls=len(fake.calls))
    if failpoint == "after_post":
        raise SimulatedPowerLoss("synthetic_crash_after_fake_post")
    settled = _settle(lab, action, reply, instant)
    return FakeResult(
        settled.state, settled.reason, attempted=True,
        post_calls=len(fake.calls))
