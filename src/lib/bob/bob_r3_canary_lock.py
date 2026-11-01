"""R3 one-run public canary source pin. COMPILED OFF without a signed release.

No environment, dashboard bit, file or model response can populate PIN.
A future independently reviewed signed package must embed ONE exact approved
run, source seal, post target and expiry. The existing publisher still requires
all normal owner/pause/budget/atomic-claim/final transport checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sqlite3

RUN = re.compile(r"\d{8}T\d{6}Z\Z")
SEAL = re.compile(r"[a-f0-9]{64}\Z")
UUID = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\Z")


@dataclass(frozen=True)
class CanaryPin:
    run: str = ""
    seal: str = ""
    target: str = ""
    expires_utc: str = ""


# Empty pins are an intentional independent fourth-layer source-level Off.
# Do not fill this from owner database settings or environment variables.
PIN = CanaryPin()


def matches_pin(pin: CanaryPin, *, run: str, seal: str, target: str,
                now: datetime, mode: str, proposal_state: str,
                queue_state: str, attempted_at, approval: tuple | None) -> bool:
    """Pure, exact, fail-closed source-pin and owner-queue check."""
    if type(pin) is not CanaryPin or type(now) is not datetime or (
            now.tzinfo is None):
        return False
    if not (RUN.fullmatch(pin.run) and SEAL.fullmatch(pin.seal)
            and UUID.fullmatch(pin.target)
            and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ",
                             pin.expires_utc or "")):
        return False
    try:
        expire = datetime.strptime(pin.expires_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        created = datetime.strptime(pin.run, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc)
        current = now.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return False
    if (current < created or current > expire
            or current - created > timedelta(days=7)
            or expire - created > timedelta(days=7)):
        return False
    return (run == pin.run and seal == pin.seal and target == pin.target
            and mode == "manual" and proposal_state == "queued"
            and queue_state == "queued" and attempted_at is None
            and approval == (pin.seal, "approved"))


def installed_canary_ready(db: sqlite3.Connection, source: Path,
                           run: str, *, now: datetime) -> bool:
    """Trusted fixed-source preflight. Caller already attested private DB.

    This checks a verified source envelope and exact independently recorded
    owner approval. A second final pin/expiry check is required before POST.
    """
    if not PIN.run:
        return False
    try:
        from bob_v08.r313c_candidate import _read_envelope, _source_seal
        from bob_r313d_owner import control_state
        state = control_state(db)
        if state["schema"] != "ready" or not state["manual"] or (
                state["automatic"]):
            return False
        action = _read_envelope(db, run)
        _, _, seal, _ = _source_seal(db, source, action)
        proposal = db.execute(
            "SELECT state FROM r3_proposals WHERE source_run=?", (run,)
        ).fetchone()
        job = db.execute(
            "SELECT state,mode,attempted_at,post_id,draft_comment,"
            "approval_sha256 FROM publish_jobs WHERE run_id=?", (run,)
        ).fetchone()
        approval = db.execute(
            "SELECT seal_sha256,decision FROM r3_owner_approvals "
            "WHERE source_run=?", (run,)
        ).fetchone()
        if not proposal or not job or (
                job[3],job[4],job[5]) != (
                    action.target_id,action.text,seal):
            return False
        if db.execute(
            "SELECT 1 FROM publish_jobs WHERE run_id<>? AND post_id=? "
            "AND attempted_at IS NOT NULL LIMIT 1",
            (run,action.target_id)).fetchone():
            return False
        return matches_pin(
            PIN,run=run,seal=seal,target=action.target_id,now=now,
            mode=job[1],proposal_state=proposal[0],queue_state=job[0],
            attempted_at=job[2],approval=approval)
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,ImportError):
        return False


def still_pinned_for_send(run: str, target: str, now: datetime) -> bool:
    """Fail closed if the exact compiled candidate expires before POST."""
    if not (PIN.run and run == PIN.run and target == PIN.target and
            type(now) is datetime and now.tzinfo is not None):
        return False
    try:
        expiry = datetime.strptime(PIN.expires_utc,"%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        return now.astimezone(timezone.utc) <= expiry
    except (ValueError,TypeError,OverflowError):
        return False
