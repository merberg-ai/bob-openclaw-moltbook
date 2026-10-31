"""R3.4 guarded source boundary and pure service-ownership cutover rehearsal.

This file has NO systemd, HTTP, credentials, release installer or live SQLite
entrypoint. The only source pinning is via real read_observation() validation.
The cutover is an immutable simulation, not commands to enable any service.
Host-specific authority and actual GET/friend proof remain unimplemented.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from typing import Literal

from .core import Action, Observation, RUN_ID, Policy, parse_decision
from .evidence import read_observation


@dataclass(frozen=True)
class SourcePin:
    source_run: str
    target_id: str
    snapshot_sha256: str
    scout_approval_sha256: str


def verified_source(source_dir: Path, action: Action, *, pinned: SourcePin | None = None
                    ) -> tuple[Observation, SourcePin]:
    """Read actual sealed Scout bytes, never trust an Observation from a model.

    Re-running this immediately before a synthetic intent detects source
    replacement, selection/approval changes, symlinks and malformed records.
    Verified means 'matches saved Scout bytes', NOT live Moltbook visibility.
    """
    if not isinstance(action, Action) or not isinstance(action.source_run, str):
        raise ValueError("untrusted_action")
    if not RUN_ID.fullmatch(action.source_run):
        raise ValueError("untrusted_source_run")
    source_dir = Path(source_dir)
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise ValueError("untrusted_source_directory")
    try:
        obs = read_observation(source_dir, action.source_run)
        payload = json.dumps({
            "type": action.kind, "source_run": action.source_run,
            "target_id": action.target_id, "reason": action.reason,
            "text": action.text,
        }, ensure_ascii=True, separators=(",", ":"))
        accepted = parse_decision(payload, obs)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        raise ValueError("source_validation_failed") from None
    if accepted != action or action.kind != "comment":
        raise ValueError("source_action_drift")
    actual = SourcePin(obs.run_id, obs.post_id,
                       obs.snapshot_sha256, obs.approval_sha256)
    if pinned is not None and actual != pinned:
        raise ValueError("source_changed_since_pin")
    return obs, actual


def simulated_pause_state(marker: Path) -> bool:
    """True means hold; only missing regular marker in private fixture is clear.

    Never accept a user/model-provided `paused=False` as an authority source.
    This is a rehearsal reader, not the final production filesystem check.
    """
    marker = Path(marker)
    if marker.name != "paused" or marker.parent.is_symlink():
        return True
    try:
        if marker.is_symlink():
            return True
        if not marker.parent.is_dir() or marker.parent.stat().st_mode & 0o077:
            return True
        return marker.exists() or marker.is_file()
    except OSError:
        return True


@dataclass(frozen=True)
class CutoverState:
    """Inert state model. No host unit changes can result from transitions."""
    phase: str = "baseline"
    legacy_publisher_timer: bool = True
    legacy_publisher_running: bool = False
    candidate_publisher_timer: bool = False
    candidate_publisher_running: bool = False
    shadow_timer: bool = True
    legacy_system_scout_timer: bool = False
    attempted: tuple[str, ...] = ()
    uncertain: tuple[str, ...] = ()


@dataclass(frozen=True)
class CutoverResult:
    state: CutoverState
    reason: str
    accepted: bool
    simulated: bool = True
    changed_host: bool = False
    published: bool = False


def _invariants(state: CutoverState) -> bool:
    if not isinstance(state, CutoverState):
        return False
    flags = (
        state.legacy_publisher_timer, state.legacy_publisher_running,
        state.candidate_publisher_timer, state.candidate_publisher_running,
        state.shadow_timer, state.legacy_system_scout_timer,
    )
    if any(type(v) is not bool for v in flags):
        return False
    if state.legacy_system_scout_timer:
        return False
    if ((state.legacy_publisher_timer or state.legacy_publisher_running) and
            (state.candidate_publisher_timer or state.candidate_publisher_running)):
        return False
    if state.phase not in ("baseline", "staged", "quiesced", "candidate"):
        return False
    if (not isinstance(state.attempted, tuple) or not isinstance(state.uncertain, tuple)
            or any(not isinstance(v, str) or len(v) > 64 for v in (
                *state.attempted, *state.uncertain))):
        return False
    return True


def rehearse_cutover(state: CutoverState, step: str, *,
                     legacy_drained: bool = False,
                     backup_verified: bool = False,
                     rollback_rehearsed: bool = False,
                     source_adapter_verified: bool = False,
                     owner_explicitly_authorized: bool = False,
                     candidate_drained: bool = False) -> CutoverResult:
    """Simulate exclusive service control, never run systemctl or read live DB.

    Step order: stage -> quiesce -> activate -> rollback. Before activation
    pause/drain old worker and verify recovery. Rollback keeps attempted and
    uncertain IDs; it changes hypothetical worker ownership only.
    """
    if not _invariants(state):
        return CutoverResult(state, "invalid_or_overlapping_dispatchers", False)
    if step not in ("stage", "quiesce", "activate", "rollback"):
        return CutoverResult(state, "unknown_transition", False)
    if step == "stage":
        if state.phase != "baseline" or not state.legacy_publisher_timer:
            return CutoverResult(state, "not_baseline", False)
        new = replace(state, phase="staged")
    elif step == "quiesce":
        if state.phase != "staged" or not legacy_drained or state.legacy_publisher_running:
            return CutoverResult(state, "legacy_not_drained", False)
        if not backup_verified or not rollback_rehearsed:
            return CutoverResult(state, "backup_or_rollback_unverified", False)
        new = replace(state, phase="quiesced", legacy_publisher_timer=False)
    elif step == "activate":
        if state.phase != "quiesced" or state.legacy_publisher_timer or state.legacy_publisher_running:
            return CutoverResult(state, "legacy_still_owned", False)
        if not (owner_explicitly_authorized and source_adapter_verified and
                backup_verified and rollback_rehearsed):
            return CutoverResult(state, "cutover_gate_not_met", False)
        new = replace(state, phase="candidate", candidate_publisher_timer=True)
    else:
        if state.phase not in ("staged", "quiesced", "candidate"):
            return CutoverResult(state, "nothing_to_roll_back", False)
        if state.candidate_publisher_running or (
                state.phase == "candidate" and not candidate_drained):
            return CutoverResult(state, "candidate_not_drained", False)
        # Code/ownership rollback MUST preserve post-intent state unchanged.
        new = replace(state, phase="baseline", legacy_publisher_timer=True,
                      legacy_publisher_running=False,
                      candidate_publisher_timer=False,
                      candidate_publisher_running=False)
    if not _invariants(new) or (new.attempted, new.uncertain) != (state.attempted, state.uncertain):
        return CutoverResult(state, "cutover_invariant_failed", False)
    return CutoverResult(new, "simulated_" + step, True)


def simulated_source_handoff(lab, source_dir: Path, action: Action, *, at: datetime,
                             mode: str, policy: Policy | None = None,
                             proof=None, pause_marker: Path | None = None,
                             after_queue=None):
    """Rehearse R3.3 using real Scout verification at 3 boundaries.

    The caller must provide an R3.3 **synthetic fixture** and an explicit
    synthetic preflight proof. An installed policy, real server proof and
    credentialed POST cannot be created here. No auto owner-consent granted.
    `after_queue` is a test-only injection point for source changes.
    """
    from .r3_unified import UnifiedLab, Outcome
    if not isinstance(lab, UnifiedLab):
        return Outcome("refused", "not_synthetic_unified_lab")
    if policy is None:
        policy = Policy()
    if pause_marker is None:
        return Outcome("refused", "no_safe_pause_source")
    try:
        obs, pin = verified_source(source_dir, action)
    except ValueError:
        return Outcome("refused", "source_unverified")
    proposed = lab.propose(action, obs, at=at)
    if proposed.state != "proposed":
        return proposed
    try:
        obs, _ = verified_source(source_dir, action, pinned=pin)
    except ValueError:
        return Outcome("refused", "source_changed_after_proposal")
    queued = lab.queue(action, obs, mode=mode, at=at, policy=policy)
    if queued.state != "queued_simulated":
        return queued
    if after_queue is not None:
        after_queue()
    try:
        obs, _ = verified_source(source_dir, action, pinned=pin)
    except ValueError:
        return Outcome("refused", "source_changed_before_pre_send")
    return lab.simulated_pre_send(
        action, obs, mode=mode, at=at, policy=policy, proof=proof,
        paused=simulated_pause_state(pause_marker))
