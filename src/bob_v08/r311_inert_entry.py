"""R3.11 inert harness callable only through the legacy publisher's explicit test CLI.

This is a rehearsal of the EXISTING executable entrypoint, not a second service.
It accepts only the marker-locked R3.3 synthetic DB, an exact private descriptor
and the fixed sibling Scout files. It NEVER imports or calls the live api(),
api_key(), credentials, systemd or a network client. Every reply is simulated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from .core import Action, RUN_ID, UUID
from .r3_unified import UnifiedLab, _utc, _validated
from .r3_cutover_rehearsal import verified_source
from .r310_atomic_claim_lab import rehearse_atomic_claim
from .r39_publisher_review import RemoteReview
from .r38_dispatch_lab import (
    InertSink, SimulatedPowerLoss, _barrier, _settle, recover_after_restart,
)

DESCRIPTOR = "r311-inert-action.json"
MAX_DESCRIPTOR_BYTES = 8192


@dataclass(frozen=True)
class InertEntrypointResult:
    state: str
    reason: str
    attempted: bool = False
    sink_calls: int = 0
    simulated: bool = True
    acted: bool = False
    dispatch_authorized: bool = False
    external_requests: int = 0
    credential_reads: int = 0
    installed_changes: int = 0


def _load_marked_input(path: Path):
    """Require explicitly private, sealed synthetic job/descriptor."""
    lab = UnifiedLab(Path(path))
    # The first access must verify exact private location and lab marker.
    db = lab._open()
    try:
        descriptor = lab.path.parent.parent / DESCRIPTOR
        if (descriptor.is_symlink() or not descriptor.is_file()
                or descriptor.stat().st_mode & 0o077
                or descriptor.stat().st_size > MAX_DESCRIPTOR_BYTES):
            raise ValueError("unsafe_inert_descriptor")
        data = json.loads(descriptor.read_bytes())
        if not isinstance(data, dict) or set(data) != {
                "run_id", "post_id", "reason", "text"}:
            raise ValueError("invalid_inert_descriptor")
        run, post = data["run_id"], data["post_id"]
        if (not isinstance(run, str) or not RUN_ID.fullmatch(run)
                or not isinstance(post, str) or not UUID.fullmatch(post)):
            raise ValueError("invalid_inert_target")
        if not isinstance(data["reason"], str) or not isinstance(data["text"], str):
            raise ValueError("invalid_inert_action")
        action = Action("comment", run, post, data["reason"], data["text"])
        job = db.execute(
            "SELECT mode,state,post_id,draft_comment,approval_sha256 "
            "FROM publish_jobs WHERE run_id=?", (run,)).fetchone()
        if (job is None or job[0] not in ("manual", "auto")
                or job[1] != "queued" or job[2] != post or job[3] != action.text):
            raise ValueError("inert_job_not_queued")
        source_root = lab.path.parent.parent / "scout"
        observed, _ = verified_source(source_root, action)
        seal, _ = _validated(action, observed)
        if job[4] != seal:
            raise ValueError("inert_seal_mismatch")
        return lab, action, job[0], observed.author
    finally:
        db.rollback()
        db.close()


def _synthetic_clock(action: Action):
    """Only fixture time, NOT a production clock or replayable send approval."""
    source_at = datetime.strptime(
        action.source_run, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return source_at + timedelta(minutes=25)


def run_inert_entry(path: Path, *, response: str = "ack",
                    fault: str = "") -> InertEntrypointResult:
    """Exercise the real publisher executable's inert command, never send.

    Faults are test-only: a crash immediately after the durable synthetic
    intent or after the fake in-memory sink sees one call. Recovery must lock
    either incomplete attempt without replay.
    """
    if response not in ("ack", "timeout", "malformed", "challenge", "rejected"):
        return InertEntrypointResult("refused", "invalid_inert_response")
    if fault not in ("", "after_intent", "after_sink"):
        return InertEntrypointResult("refused", "invalid_inert_fault")
    try:
        lab, action, mode, expected_author = _load_marked_input(Path(path))
        at = _synthetic_clock(action)
    except (ValueError, OSError, sqlite3.Error, TypeError, UnicodeError):
        return InertEntrypointResult("refused", "invalid_private_inert_fixture")
    source = lab.path.parent.parent / "scout"
    pause = lab.path.parent.parent / "paused"
    # Deliberate in-memory fake response: NO network endpoint or credentials.
    get_post = lambda post, author: RemoteReview(
        post == action.target_id and author.casefold() == expected_author.casefold(),
        "synthetic_exact_target")
    claimed = rehearse_atomic_claim(
        lab, action, mode=mode, clock=lambda: at,
        public_get=get_post)
    if claimed.state != "claimed_simulated":
        return InertEntrypointResult(
            "refused", claimed.reason, attempted=claimed.attempted_at_recorded)
    if fault == "after_intent":
        raise SimulatedPowerLoss("r311_crash_after_synthetic_intent")
    barrier = _barrier(lab, source, action, mode, pause, at)
    if barrier != "clear":
        lab.simulated_uncertain(action.source_run, at=at)
        return InertEntrypointResult(
            "uncertain_simulated", "barrier_" + barrier, attempted=True)
    sink = InertSink(response)
    try:
        receipt = sink.deliver(action.target_id, action.text)
    except Exception:
        lab.simulated_uncertain(action.source_run, at=at)
        return InertEntrypointResult(
            "uncertain_simulated", "synthetic_sink_unknown",
            attempted=True, sink_calls=len(sink.calls))
    if fault == "after_sink":
        raise SimulatedPowerLoss("r311_crash_after_inert_sink")
    settled = _settle(lab, action, receipt, at)
    return InertEntrypointResult(
        settled.state, settled.reason, attempted=True,
        sink_calls=len(sink.calls))


def recover_inert_entry(path: Path) -> InertEntrypointResult:
    """Manual *fixture-only* restart check. Never calls the fake sink."""
    try:
        lab = UnifiedLab(Path(path))
        db = lab._open()
        db.rollback()
        db.close()
        answer = recover_after_restart(lab, at=datetime.now(timezone.utc))
        return InertEntrypointResult(
            "recovered_simulated", "no_replay",
            attempted=answer.uncertain_locks > 0)
    except (ValueError, OSError, sqlite3.Error, TypeError):
        return InertEntrypointResult("refused", "invalid_private_inert_fixture")
