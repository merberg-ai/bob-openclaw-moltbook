"""R3.13c source-only candidate for the EXISTING single publisher.

This is the prospective R3 branch, not a second publisher. Only the existing
publisher's fixed-root caller may supply public GET, legacy POST/credential
transport and UTC clock. The real entrypoint has an independent hardcoded Off
switch; tests use private synthetic SQLite, fake GET and in-memory fake POST.

Never accept a model-provided host, path, proof, owner permission, HTTP client,
or arbitrary action. Bob's action MUST be recoverable from a durable sealed
envelope. R3.5's proposals alone do not persist the decision reason required
to recompute the R3 fingerprint.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .core import Action, RUN_ID, UUID
from .r3_cutover_rehearsal import verified_source, simulated_pause_state
from .r3_unified import _validated, _utc
from .r37_trusted_gate_lab import _read_friends
from .r39_publisher_review import (
    review_publisher_admission, _local_review, PREFLIGHT_MAX_AGE,
)
from .r313b_upgrade_contract import review_permission
from bob_activity_limits import read_limits

ENVELOPE_TABLE = "r313c_action_envelopes"
ENVELOPE_DDL = """CREATE TABLE r313c_action_envelopes(
    source_run TEXT PRIMARY KEY,
    action_json TEXT NOT NULL,
    action_sha256 TEXT NOT NULL,
    seal_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL)"""
MAX_ACTION_BYTES = 8192
MAX_UTC_DRIFT = PREFLIGHT_MAX_AGE
NO_LIVE_AUTHORITY = False  # This module never asserts permission to POST.


@dataclass(frozen=True)
class CandidateResult:
    status: str
    reason: str
    attempted: bool = False
    transport_calls: int = 0
    external_requests: int = 0
    dispatch_authorized: bool = False


def canonical_action(action: Action) -> str:
    if type(action) is not Action or action.kind != "comment":
        raise ValueError("unsupported_action")
    return json.dumps({
        "type": action.kind,
        "source_run": action.source_run,
        "target_id": action.target_id,
        "reason": action.reason,
        "text": action.text,
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _read_envelope(db: sqlite3.Connection, run: str) -> Action:
    if not isinstance(run, str) or not RUN_ID.fullmatch(run):
        raise ValueError("invalid_source_run")
    row = db.execute(
        "SELECT action_json,action_sha256,seal_sha256 FROM "
        "r313c_action_envelopes WHERE source_run=?", (run,)).fetchone()
    if row is None:
        raise ValueError("missing_sealed_action_envelope")
    raw, digest, stored_seal = row
    if not isinstance(raw, str) or not 0 < len(raw.encode("utf-8")) <= MAX_ACTION_BYTES:
        raise ValueError("action_envelope_size")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != digest:
        raise ValueError("action_envelope_digest")
    obj = json.loads(raw)
    if not isinstance(obj, dict) or set(obj) != {
            "type", "source_run", "target_id", "reason", "text"}:
        raise ValueError("action_envelope_shape")
    if any(not isinstance(value, str) for value in obj.values()):
        raise ValueError("action_envelope_type")
    action = Action(obj["type"], obj["source_run"],
                    obj["target_id"], obj["reason"], obj["text"])
    if action.source_run != run or canonical_action(action) != raw:
        raise ValueError("action_envelope_not_canonical")
    if (not isinstance(stored_seal, str) or len(stored_seal) != 64
            or not all(c in "0123456789abcdef" for c in stored_seal)):
        raise ValueError("action_envelope_seal_invalid")
    # Seal is checked against SAVED Scout observation below, not trusted here.
    return action


def _source_seal(db: sqlite3.Connection, source: Path, action: Action):
    observation, pin = verified_source(source, action)
    seal, fingerprint = _validated(action, observation)
    envelope = db.execute(
        "SELECT action_json,action_sha256,seal_sha256 FROM "
        "r313c_action_envelopes WHERE source_run=?", (action.source_run,)).fetchone()
    raw = canonical_action(action)
    if envelope != (raw, hashlib.sha256(raw.encode()).hexdigest(), seal):
        raise ValueError("envelope_or_source_seal_changed")
    return observation, pin, seal, fingerprint


def _head(db: sqlite3.Connection):
    # Exact whole-queue manual-first priority, rather than the R3.12 legacy-
    # only selector that deliberately bypasses held R3 rows when hard Off.
    head = db.execute(
        "SELECT run_id FROM publish_jobs WHERE state='queued' "
        "ORDER BY CASE WHEN mode='manual' THEN 0 ELSE 1 END, "
        "created_at ASC,run_id ASC LIMIT 1").fetchone()
    if not head:
        return None
    row = db.execute(
        "SELECT 1 FROM r3_proposals WHERE source_run=?", head).fetchone()
    return head[0] if row else None


def _owner_gate(db, action: Action, mode: str, seal: str) -> bool:
    return review_permission(
        db, mode=mode, source_run=action.source_run,
        seal_sha256=seal).category == "reviewed"


def _after_intent(db: sqlite3.Connection, source: Path, pause: Path,
                  action: Action, mode: str, at: datetime,
                  original_pin, original_seal: str,
                  original_fingerprint: str) -> str:
    """Reinspect filesystem + owner + friend + queue + limits AFTER commit.

    R3 intent was already counted; budget checks accept exactly the consumed
    slot but refuse reduced caps and another competing recent attempt.
    """
    if simulated_pause_state(pause):
        return "paused_or_untrusted"
    try:
        obs, pin, seal, fingerprint = _source_seal(db, source, action)
        if (pin, seal, fingerprint) != (
                original_pin, original_seal, original_fingerprint):
            return "source_drift_after_intent"
        row = db.execute(
            "SELECT mode,state,approval_sha256,post_id,draft_comment,attempted_at "
            "FROM publish_jobs WHERE run_id=?", (action.source_run,)).fetchone()
        if (row is None or row[:5] != (
                mode, "sending", seal, action.target_id, action.text)
                or not isinstance(row[5], str) or not row[5]):
            return "intent_changed"
        proposal = db.execute(
            "SELECT post_id,draft_comment,seal_sha256,fingerprint,"
            "snapshot_sha256,state FROM r3_proposals WHERE source_run=?",
            (action.source_run,)).fetchone()
        if proposal != (
                action.target_id, action.text, seal, fingerprint,
                pin.snapshot_sha256, "intent"):
            return "proposal_changed"
        if not _owner_gate(db, action, mode, seal):
            return "independent_owner_permission_revoked"
        if mode == "auto":
            friend = _read_friends(db, source, action, obs)
            if friend != "clear":
                return "friend_" + friend
        # Manual requires a separate exact Bob-authored owner approval, not
        # the legacy Scout 'decisions' approval.
        if db.execute(
            "SELECT 1 FROM decisions WHERE run_id=?", (action.source_run,)).fetchone():
            return "legacy_decision_collision"
        if db.execute(
            "SELECT 1 FROM publish_jobs WHERE run_id<>? AND post_id=? "
            "AND (attempted_at IS NOT NULL OR state IN "
            "('sending','uncertain','published','verified_unconfirmed',"
            "'awaiting_verification','verifying','verification_expired',"
            "'verification_failed')) LIMIT 1",
            (action.source_run, action.target_id)).fetchone():
            return "another_attempted_target"
        cfg = read_limits(db)
        stamp = _utc(at)
        attempted = db.execute(
            "SELECT run_id,mode,attempted_at FROM publish_jobs "
            "WHERE attempted_at IS NOT NULL").fetchall()
        day = stamp.strftime("%Y-%m-%d")
        count = auto_count = 0
        for rid, job_mode, value in attempted:
            if not isinstance(value, str):
                return "attempt_history_corrupt"
            when = _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
            if when > stamp:
                return "future_attempt_history"
            if when.strftime("%Y-%m-%d") == day:
                count += 1
                auto_count += job_mode == "auto"
            if rid != action.source_run and stamp - when < timedelta(
                    minutes=cfg["comment_gap_minutes"]):
                return "competing_spacing_or_new_attempt"
        if count > cfg["comment_daily"] or (
                mode == "auto" and auto_count > cfg["comment_auto_daily"]):
            return "budget_reduced_after_intent"
        if simulated_pause_state(pause):
            return "paused_after_intent"
        return "clear"
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        return "final_boundary_unavailable"


def _record_outcome(db: sqlite3.Connection, run: str, status: str,
                    event: str, at: str, *, comment_id=None,
                    challenge=None) -> None:
    """One ledger; no automatic requeue and no guessed public confirmation."""
    db.execute("BEGIN IMMEDIATE")
    try:
        if status not in ("uncertain", "published", "awaiting_verification"):
            raise ValueError("invalid_candidate_outcome")
        kwargs = challenge or ("", "", "")
        changed = db.execute(
            "UPDATE publish_jobs SET state=?,comment_id=?,challenge_code=?,"
            "challenge_text=?,challenge_expires_at=?,updated_at=? WHERE run_id=? "
            "AND state='sending' AND attempted_at IS NOT NULL",
            (status, comment_id, kwargs[0], kwargs[1], kwargs[2], at, run))
        if changed.rowcount != 1:
            raise ValueError("send_intent_changed_before_receipt")
        changed = db.execute(
            "UPDATE r3_proposals SET state=?,updated_at=? WHERE source_run=? "
            "AND state='intent'", (status, at, run))
        if changed.rowcount != 1:
            raise ValueError("proposal_intent_changed_before_receipt")
        db.execute("INSERT INTO r3_lab_audit(source_run,event,reason,at) "
                   "VALUES(?,?,?,?)", (run, "r313c_receipt", event, at))
        db.commit()
    except BaseException:
        db.rollback()
        raise


def _claim(db: sqlite3.Connection, source: Path, pause: Path,
           action: Action, mode: str, seal: str, fingerprint: str,
           pin, at: datetime) -> bool:
    """Publisher-owned BEGIN IMMEDIATE over SAME legacy publish_jobs ledger."""
    db.execute("BEGIN IMMEDIATE")
    try:
        reason, identity = _local_review(
            db, source, action, mode=mode, at=at, pause_marker=pause)
        if identity is None or identity[0] != pin:
            db.rollback()
            return False
        observed, current_pin, new_seal, new_fingerprint = _source_seal(
            db, source, action)
        if (current_pin, new_seal, new_fingerprint) != (
                pin, seal, fingerprint):
            db.rollback()
            return False
        if not _owner_gate(db, action, mode, seal):
            db.rollback()
            return False
        if simulated_pause_state(pause):
            db.rollback()
            return False
        now = _utc(at).isoformat()
        sql = (
            "UPDATE publish_jobs SET state='sending',attempted_at=?,updated_at=? "
            "WHERE run_id=? AND state='queued' AND attempted_at IS NULL "
            "AND mode=? AND approval_sha256=? AND post_id=? AND draft_comment=? "
            "AND EXISTS(SELECT 1 FROM r3_proposals p "
            "WHERE p.source_run=publish_jobs.run_id AND p.state='queued' "
            "AND p.post_id=publish_jobs.post_id AND "
            "p.draft_comment=publish_jobs.draft_comment AND "
            "p.seal_sha256=publish_jobs.approval_sha256 AND "
            "p.fingerprint=? AND p.snapshot_sha256=?)"
        )
        row = db.execute(sql, (
            now, now, action.source_run, mode, seal,
            action.target_id, action.text, fingerprint,
            pin.snapshot_sha256))
        if row.rowcount != 1:
            db.rollback()
            return False
        changed = db.execute(
            "UPDATE r3_proposals SET state='intent',updated_at=? "
            "WHERE source_run=? AND state='queued' AND seal_sha256=? "
            "AND fingerprint=? AND snapshot_sha256=?",
            (now, action.source_run, seal, fingerprint,
             pin.snapshot_sha256))
        if changed.rowcount != 1:
            db.rollback()
            return False
        db.execute("INSERT INTO r3_lab_audit(source_run,event,reason,at) "
                   "VALUES(?,?,?,?)", (action.source_run, "r313c_claim",
                                      "counted_durable_intent", now))
        db.commit()
        return True
    except BaseException:
        db.rollback()
        raise


def candidate_step(db: sqlite3.Connection, source: Path, pause: Path,
                   *, clock, public_get, post_comment,
                   after_intent=None, after_post=None) -> CandidateResult:
    """Prospective single publisher branch, callable only by a trusted wrapper.

    source/pause/clock/transport are supplied by the fixed installed publisher
    wrapper, NEVER by the model or a public user. In tests they are injected
    fake callbacks against a marker-verified synthetic database. This function
    is not reachable from the normal installed publisher while hard Off.
    """
    calls = 0
    try:
        run = _head(db)
        if run is None:
            return CandidateResult("not_selected", "legacy_head_or_empty")
        action = _read_envelope(db, run)
        obs, pin, seal, fingerprint = _source_seal(db, source, action)
        job = db.execute(
            "SELECT mode FROM publish_jobs WHERE run_id=?", (run,)).fetchone()
        mode = job[0] if job else None
        if mode not in ("manual", "auto") or not _owner_gate(
                db, action, mode, seal):
            return CandidateResult("held", "separate_r3_owner_consent_missing")
        before = _utc(clock())
        review = review_publisher_admission(
            db, source, action, mode=mode, pause_marker=pause,
            clock=clock, public_get=public_get)
        if review.status != "reviewed":
            return CandidateResult("held", "review_" + review.reason)
        at = _utc(clock())
        if at < before or at - before > MAX_UTC_DRIFT:
            return CandidateResult("held", "stale_preflight_clock")
        if not _claim(db, source, pause, action, mode, seal, fingerprint,
                      pin, at):
            return CandidateResult("held", "stale_claim_or_owner_revoked")
    except (OSError, ValueError, TypeError, sqlite3.Error, KeyError):
        return CandidateResult("held", "candidate_admission_unavailable")
    # Durable counted attempt now exists: from here no retry, regardless of
    # pause, crash, network timeout or ambiguous HTTP response.
    if after_intent is not None:
        after_intent()  # synthetic test hook; normal publisher passes NONE
    final = _after_intent(
        db, source, pause, action, mode, _utc(clock()), pin, seal, fingerprint)
    if final != "clear":
        try:
            _record_outcome(db, run, "uncertain",
                            "post_intent_hold_" + final, _utc(clock()).isoformat())
        except (OSError, ValueError, sqlite3.Error):
            pass  # Still locked as 'sending', never requeued.
        return CandidateResult("uncertain", "post_intent_" + final, attempted=True)
    calls += 1
    try:
        # The authenticated wrapper is the *existing* single publisher, and
        # its fixed URL and credential access are outside this module.
        reply = post_comment(action.target_id, action.text)
    except Exception:
        reply = None
    if after_post is not None:
        after_post()  # synthetic crash after fake transport, before receipt
    status = "uncertain"
    cid = None
    challenge = None
    event = "unknown_or_rejected_response_no_retry"
    if isinstance(reply, dict) and reply.get("success") is True:
        data = reply.get("data") if isinstance(reply.get("data"), dict) else reply
        verification = data.get("verification")
        if not isinstance(verification, dict):
            verification = reply.get("verification")
        if data.get("verification_required") is True or reply.get(
                "verification_required") is True or isinstance(verification, dict):
            v = verification if isinstance(verification, dict) else {}
            code = v.get("verification_code")
            question = v.get("challenge_text")
            if (isinstance(code, str) and code.startswith("moltbook_")
                    and isinstance(question, str) and question.strip()
                    and len(code) <= 150 and len(question) <= 2000):
                status = "awaiting_verification"
                challenge = (code, question, str(v.get("expires_at") or "")[:60])
                event = "human_challenge_required_no_auto_retry"
        else:
            comment = data.get("comment")
            if not isinstance(comment, dict):
                comment = reply.get("comment")
            cid = (comment.get("id") if isinstance(comment, dict)
                   else data.get("comment_id") or reply.get("comment_id"))
            if isinstance(cid, str) and UUID.fullmatch(cid):
                status = "published"
                # This is API ACK only; not independently public verified.
                event = "api_ack_comment_id_not_publicly_reverified"
            else:
                cid = None
    try:
        _record_outcome(db, run, status, event, _utc(clock()).isoformat(),
                        comment_id=cid, challenge=challenge)
    except (OSError, sqlite3.Error, ValueError):
        # Durable state stays sending if record of response is unavailable.
        return CandidateResult("uncertain", "receipt_record_unavailable",
                               attempted=True, transport_calls=calls)
    return CandidateResult(
        "api_acknowledged" if status == "published" else status, event,
        attempted=True, transport_calls=calls)


def recover_inflight(db: sqlite3.Connection) -> int:
    """Never replay an R3 sending row after interruption or process restart."""
    db.execute("BEGIN IMMEDIATE")
    try:
        rows = db.execute(
            "SELECT j.run_id FROM publish_jobs j JOIN r3_proposals p "
            "ON p.source_run=j.run_id WHERE j.state='sending' "
            "AND j.attempted_at IS NOT NULL AND p.state='intent'").fetchall()
        for (run,) in rows:
            db.execute(
                "UPDATE publish_jobs SET state='uncertain' WHERE run_id=? "
                "AND state='sending' AND attempted_at IS NOT NULL", (run,))
            db.execute(
                "UPDATE r3_proposals SET state='uncertain' WHERE source_run=? "
                "AND state='intent'", (run,))
            db.execute(
                "INSERT INTO r3_lab_audit(source_run,event,reason,at) "
                "VALUES(?,?,?,?)", (
                    run, "r313c_recovered",
                    "interrupted_attempt_never_replayed",
                    datetime.now(timezone.utc).isoformat()))
        db.commit()
        return len(rows)
    except BaseException:
        db.rollback()
        raise
