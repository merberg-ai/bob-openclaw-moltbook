"""R3.8 inert publisher lifecycle rehearsal, not an executable publisher.

One EXISTING R3.3 marked synthetic SQLite ledger records a counted intent;
an in-memory scripted sink simulates a remote response. A process crash after
intent or after a simulated acknowledgement NEVER permits re-dispatch.
No HTTP client, credentials, service controls, or live SQLite paths exist.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import sqlite3

from .core import Action
from .r3_cutover_rehearsal import simulated_pause_state, verified_source
from .r3_unified import UnifiedLab, _validated, _utc, _ts
from .r37_trusted_gate_lab import rehearse_trusted_gate, _read_friends
from bob_activity_limits import read_limits

ACK_ID = "11111111-1111-4111-8111-111111111111"


@dataclass(frozen=True)
class DispatchResult:
    state: str
    reason: str
    simulated: bool = True
    acted: bool = False
    dispatched_to_moltbook: bool = False


@dataclass(frozen=True)
class RecoveryResult:
    uncertain_locks: int
    preexisting_legacy_sends_for_review: int
    invalid_synthetic_intents: int
    safe_to_auto_retry: bool = False
    simulated: bool = True
    changed_host: bool = False


class SimulatedPowerLoss(RuntimeError):
    pass


class InertSink:
    """Only in-memory receipts. This class has no network-facing operations."""

    def __init__(self, response="ack", *, comment_id=ACK_ID):
        if response not in ("ack", "timeout", "malformed", "challenge", "rejected"):
            raise ValueError("invalid_inert_response")
        self.response = response
        self.comment_id = comment_id
        self.calls = []

    def deliver(self, target: str, body: str):
        self.calls.append(hashlib.sha256(
            (target + "\n" + body).encode("utf-8")).hexdigest())
        if self.response == "timeout":
            raise TimeoutError("synthetic_unknown_delivery")
        if self.response == "rejected":
            return {"success": False}
        if self.response == "malformed":
            return {"success": True}
        if self.response == "challenge":
            # Verification is a separate human-controlled workflow.
            return {"verification_required": True}
        return {"success": True, "comment": {"id": self.comment_id}}


def _barrier(lab: UnifiedLab, source_dir, action: Action, mode: str,
             pause_marker, at: datetime) -> str:
    """Final fresh *synthetic* check after intent, immediately before sink.

    Because the prior atomic intent already consumed this job's rate slot,
    compare actual attempts against freshly validated limits using >, not >=.
    No independent attempt ledger is created.
    """
    if simulated_pause_state(pause_marker):
        return "paused_at_dispatch_barrier"
    try:
        observation, pin = verified_source(source_dir, action)
        seal, fingerprint = _validated(action, observation)
    except (OSError, ValueError, TypeError):
        return "source_changed_after_intent"
    db = lab._open()
    try:
        job = db.execute(
            "SELECT mode,state,approval_sha256,post_id,draft_comment,attempted_at "
            "FROM publish_jobs WHERE run_id=?", (action.source_run,)).fetchone()
        if (job is None or job[:5] != (
                mode, "sending_simulated", seal, action.target_id, action.text)
                or not isinstance(job[5], str) or not job[5]):
            return "synthetic_intent_changed"
        proposal = db.execute(
            "SELECT post_id,draft_comment,seal_sha256,fingerprint,snapshot_sha256,state "
            "FROM r3_proposals WHERE source_run=?", (action.source_run,)).fetchone()
        if proposal != (action.target_id, action.text, seal, fingerprint,
                        pin.snapshot_sha256, "intent_simulated"):
            return "sealed_proposal_changed"
        dial_row = db.execute(
            "SELECT value FROM publish_settings WHERE name='r3_comment_dial'").fetchone()
        dial = dial_row[0] if dial_row else "off"
        if dial not in ("auto", "propose") or (mode == "auto" and dial != "auto"):
            return "owner_dial_revoked"
        if mode == "auto":
            flags = dict(db.execute("SELECT name,value FROM publish_settings "
                                    "WHERE name IN ('auto_enabled','r3_auto_enabled','r3_auto_since')"))
            if flags.get("auto_enabled") != "1" or flags.get("r3_auto_enabled") != "1":
                return "auto_consent_revoked"
            try:
                since = _utc(datetime.fromisoformat(
                    flags["r3_auto_since"].replace("Z", "+00:00")))
                created = datetime.strptime(
                    action.source_run, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError, TypeError, KeyError):
                return "auto_consent_age_unverified"
            if created <= since:
                return "source_predates_auto_consent"
            if db.execute("SELECT 1 FROM decisions WHERE run_id=?",
                          (action.source_run,)).fetchone():
                return "legacy_owner_override"
            friend = _read_friends(db, source_dir, action, observation)
            if friend != "clear":
                return friend
        elif mode == "manual":
            approved = db.execute(
                "SELECT seal_sha256,decision FROM r3_owner_approvals WHERE source_run=?",
                (action.source_run,)).fetchone()
            if approved != (seal, "approved"):
                return "manual_consent_revoked"
        else:
            return "invalid_mode"
        if db.execute(
                "SELECT 1 FROM publish_jobs WHERE run_id<>? AND post_id=? AND "
                "(attempted_at IS NOT NULL OR state IN "
                "('sending','uncertain','published','verified_unconfirmed',"
                "'awaiting_verification','verifying','verification_expired',"
                "'verification_failed','sending_simulated')) LIMIT 1",
                (action.source_run, action.target_id)).fetchone():
            return "competing_attempted_target"
        config = read_limits(db)
        day = _utc(at).strftime("%Y-%m-%d")
        total = db.execute(
            "SELECT COUNT(*) FROM publish_jobs WHERE attempted_at LIKE ?",
            (day + "%",)).fetchone()[0]
        automatic = db.execute(
            "SELECT COUNT(*) FROM publish_jobs WHERE attempted_at LIKE ? AND mode='auto'",
            (day + "%",)).fetchone()[0]
        if total > config["comment_daily"] or (
                mode == "auto" and automatic > config["comment_auto_daily"]):
            return "budget_reduced_after_intent"
        # Unknown/replaced attempted_at history never creates fresh permission.
        attempted = db.execute(
            "SELECT attempted_at FROM publish_jobs WHERE attempted_at IS NOT NULL"
        ).fetchall()
        for (value,) in attempted:
            if not isinstance(value, str):
                return "invalid_attempted_history"
            try:
                instant = _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
            except (ValueError, TypeError, AttributeError):
                return "invalid_attempted_history"
            if instant > _utc(at):
                return "future_attempted_history"
        if simulated_pause_state(pause_marker):
            return "paused_at_dispatch_barrier"
        return "clear"
    except (ValueError, sqlite3.Error, TypeError):
        return "dispatch_boundary_unavailable"
    finally:
        db.rollback()
        db.close()


def _settle(lab: UnifiedLab, action: Action, response: dict, at: datetime
            ) -> DispatchResult:
    """Persist simulated receipt in one transaction; never mark public published."""
    state, reason, cid = ("uncertain_simulated", "ambiguous_receipt", None)
    if isinstance(response, dict) and response.get("success") is True:
        comment = response.get("comment")
        if isinstance(comment, dict):
            ident = comment.get("id")
            from .core import UUID
            if isinstance(ident, str) and UUID.fullmatch(ident):
                state, reason, cid = ("acknowledged_simulated", "synthetic_ack_only", ident)
        if state == "uncertain_simulated" and response.get("verification_required") is True:
            state, reason = ("awaiting_verification_simulated", "human_verification_required")
    db = lab._open()
    try:
        job = db.execute(
            "SELECT state,attempted_at FROM publish_jobs WHERE run_id=?",
            (action.source_run,)).fetchone()
        proposal = db.execute(
            "SELECT state FROM r3_proposals WHERE source_run=?",
            (action.source_run,)).fetchone()
        if (not job or job[0] != "sending_simulated" or not job[1]
                or proposal != ("intent_simulated",)):
            db.commit()
            return DispatchResult("refused", "receipt_not_pending")
        stamp = _ts(at)
        db.execute(
            "UPDATE publish_jobs SET state=?,comment_id=?,updated_at=? "
            "WHERE run_id=? AND state='sending_simulated' AND attempted_at IS NOT NULL",
            (state, cid, stamp, action.source_run))
        db.execute(
            "UPDATE r3_proposals SET state=?,updated_at=? "
            "WHERE source_run=? AND state='intent_simulated'",
            (state, stamp, action.source_run))
        db.execute("INSERT INTO r3_lab_audit VALUES(NULL,?,?,?,?)",
                   (action.source_run, "r38_receipt", reason, stamp))
        db.commit()
        return DispatchResult(state, reason)
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def simulate_dispatch(lab: UnifiedLab, source_dir, action: Action, *, mode: str,
                      pause_marker, get_post, clock, sink: InertSink,
                      failpoint: str = "", after_intent=None) -> DispatchResult:
    """Only this call stack may trigger the single in-memory delivery event.

    A restart CANNOT call this function on a prior 'sending_simulated' job:
    the R3.7 gate only accepts queued/never-attempted work. A stored intent
    alone is not a replay permit.
    """
    if type(sink) is not InertSink:
        return DispatchResult("refused", "not_an_inert_sink")
    if failpoint not in ("", "after_intent", "after_sink"):
        return DispatchResult("refused", "invalid_failpoint")
    result = rehearse_trusted_gate(
        lab, source_dir, action, mode=mode, pause_marker=pause_marker,
        get_post=get_post, clock=clock)
    if result.state != "intent_simulated":
        return DispatchResult("refused", result.reason)
    if failpoint == "after_intent":
        raise SimulatedPowerLoss("synthetic_crash_after_durable_intent")
    if after_intent is not None:
        after_intent()  # tests may mutate private synthetic database only
    at = _utc(clock())
    barrier = _barrier(lab, source_dir, action, mode, pause_marker, at)
    if barrier != "clear":
        lab.simulated_uncertain(action.source_run, at=at)
        # The slot remains spent even though this inert sink did NOT fire.
        return DispatchResult("uncertain_simulated", "barrier_" + barrier)
    try:
        response = sink.deliver(action.target_id, action.text)
    except Exception:
        lab.simulated_uncertain(action.source_run, at=at)
        return DispatchResult("uncertain_simulated", "synthetic_transport_unknown")
    if failpoint == "after_sink":
        raise SimulatedPowerLoss("synthetic_crash_after_inert_sink")
    return _settle(lab, action, response, at)


def recover_after_restart(lab: UnifiedLab, *, at: datetime) -> RecoveryResult:
    """One-way reconciliation, NEVER calling a transport or resetting attempts.

    Legacy 'sending' rows are left untouched and reported for manual review.
    """
    db = lab._open()
    try:
        stale = db.execute(
            "SELECT j.run_id,j.attempted_at,p.state FROM publish_jobs j "
            "LEFT JOIN r3_proposals p ON p.source_run=j.run_id "
            "WHERE j.state='sending_simulated'").fetchall()
        converted, invalid = 0, 0
        for rid, attempted, proposal in stale:
            if not attempted or proposal != "intent_simulated":
                invalid += 1
                continue
            stamp = _ts(at)
            db.execute(
                "UPDATE publish_jobs SET state='uncertain_simulated',updated_at=? "
                "WHERE run_id=? AND state='sending_simulated' "
                "AND attempted_at IS NOT NULL", (stamp, rid))
            db.execute(
                "UPDATE r3_proposals SET state='uncertain_simulated',updated_at=? "
                "WHERE source_run=? AND state='intent_simulated'", (stamp, rid))
            db.execute("INSERT INTO r3_lab_audit VALUES(NULL,?,?,?,?)",
                       (rid, "r38_recovery", "no_automatic_retry", stamp))
            converted += 1
        legacy = db.execute(
            "SELECT COUNT(*) FROM publish_jobs WHERE state IN "
            "('sending','uncertain','verified_unconfirmed','verifying',"
            "'awaiting_verification','verification_expired','verification_failed')"
        ).fetchone()[0]
        db.commit()
        return RecoveryResult(converted, legacy, invalid)
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
