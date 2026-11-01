"""R3 one-run public canary source pin. Install and queue stay OFF until explicitly armed.

No environment, dashboard bit, file or model response can populate PIN.
This reviewed signed candidate embeds ONE exact approved
run, source seal, post target and expiry. The existing publisher still requires
all normal owner/pause/budget/atomic-claim/final transport checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import stat
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


# Immutable source pin is only the first gate. A separate private owner-arm
# marker is required before this source can dispatch. Never derive from DB.
PIN = CanaryPin(
    run="20261101T151033Z",
    seal="870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2",
    target="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a",
    expires_utc="2026-11-05T00:00:00Z",
)

ARM_FORMAT = "bob-r3-canary-arm-v1"
ARM_NAME = "r3-canary-once.json"


def arm_path() -> Path:
    return Path.home() / ".config/bob-system" / ARM_NAME


def expected_marker() -> dict:
    return {"format": ARM_FORMAT, "run": PIN.run, "seal": PIN.seal,
            "target": PIN.target, "expires_utc": PIN.expires_utc}


def marker_valid(*, now: datetime) -> bool:
    """One explicit private owner arm file; never created by publisher or UI.

    Arm is a local manual capability, NOT the public POST. The exact sealed
    job, admission, pause, rate, duplicate and attempted-at gates still apply.
    """
    path=arm_path()
    try:
        if not isinstance(now, datetime) or now.tzinfo is None:
            return False
        created=datetime.strptime(PIN.run,"%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc)
        expires=datetime.strptime(PIN.expires_utc,"%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        stamp=now.astimezone(timezone.utc)
        if not created <= stamp <= expires or stamp-created > timedelta(days=7):
            return False
        parent=path.parent.lstat()
        leaf=path.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=os.geteuid()
                or parent.st_mode & 0o077 or not stat.S_ISREG(leaf.st_mode)
                or leaf.st_uid!=os.geteuid() or leaf.st_nlink!=1
                or leaf.st_mode & 0o177 or not 0 < leaf.st_size < 1024):
            return False
        return json.loads(path.read_text(encoding="utf-8"))==expected_marker()
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
        return False





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
    if not marker_valid(now=now):
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
        return now.astimezone(timezone.utc) <= expiry and marker_valid(now=now)
    except (ValueError,TypeError,OverflowError):
        return False
