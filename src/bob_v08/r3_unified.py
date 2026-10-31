"""R3.3 offline unified handoff laboratory. NEVER a production publisher.

One marked, private, synthetic database holds sealed Bob-authored proposals,
explicit owner decisions, legacy-shaped publish_jobs and attempted_at history.
The only simulated sending intent is committed atomically with both ledgers.
There is NO API, credential, systemd or live filesystem integration; a positive
result is never authorization to contact Moltbook. Shadow4 is unaffected.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

from .core import Action, Observation, Policy, PolicyState, check, parse_decision

LIB = str(Path(__file__).resolve().parents[1] / "lib" / "bob")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
from bob_activity_limits import allowed as legacy_allowed, attempts, last_attempt  # noqa: E402

LAB_FOLDER = "r3-unified-fixtures"
LAB_FILE = "r3-unified-lab.sqlite3"
MARKER = "r3-unified-synthetic-only-v1"
SHA = re.compile(r"[a-f0-9]{64}\Z")
RUN = re.compile(r"\d{8}T\d{6}Z\Z")
BLOCKED = ("sending", "uncertain", "published", "verified_unconfirmed",
           "awaiting_verification", "verifying", "verification_expired",
           "sending_simulated", "uncertain_simulated")


@dataclass(frozen=True)
class Outcome:
    state: str
    reason: str
    simulated: bool = True
    acted: bool = False


@dataclass(frozen=True)
class Proof:
    """Synthetic trusted GET/friend result. Models must NEVER supply this."""
    post_id: str
    checked_at: datetime
    friend_status: str = "unknown"  # clear | protected | unknown


def _utc(at):
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("invalid_lab_clock")
    return at.astimezone(timezone.utc)


def _ts(at):
    return _utc(at).isoformat(timespec="microseconds")


def _validated(action, observation):
    if not isinstance(action, Action) or not isinstance(observation, Observation):
        raise ValueError("invalid_lab_action")
    if not all(isinstance(v, str) and SHA.fullmatch(v)
               for v in (observation.snapshot_sha256, observation.approval_sha256)):
        raise ValueError("unverified_lab_source")
    raw = json.dumps({
        "type": action.kind, "source_run": action.source_run,
        "target_id": action.target_id, "reason": action.reason, "text": action.text,
    }, ensure_ascii=True, sort_keys=True)
    try:
        accepted = parse_decision(raw, observation)
    except (ValueError, TypeError):
        raise ValueError("invalid_lab_action") from None
    if accepted != action or action.kind != "comment":
        raise ValueError("unsupported_lab_action")
    # A new Bob-authored comment gets its OWN seal, not the old Scout approval.
    seal = hashlib.sha256((observation.post_id + "\n" + action.text + "\n" +
                           observation.snapshot_sha256).encode("utf-8")).hexdigest()
    fingerprint = hashlib.sha256((seal + "\n" + action.reason + "\n" +
                                  observation.run_id).encode("utf-8")).hexdigest()
    return seal, fingerprint


class UnifiedLab:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _open(self):
        p = self.path
        if p.name != LAB_FILE or p.parent.name != LAB_FOLDER:
            raise ValueError("not_unified_lab_path")
        if (p.is_symlink() or p.parent.is_symlink() or not p.is_file()
                or not p.parent.is_dir() or p.stat().st_mode & 0o077
                or p.parent.stat().st_mode & 0o077):
            raise ValueError("unsafe_unified_lab_fixture")
        db = sqlite3.connect(p, timeout=4, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=4000")
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT value FROM r3_lab_meta WHERE name='contract'").fetchone() != (MARKER,):
                raise ValueError("untrusted_unified_lab_marker")
            return db
        except BaseException:
            db.rollback()
            db.close()
            raise

    @staticmethod
    def _finish(db, fn):
        try:
            result = fn(db)
            db.commit()
            return result
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def propose(self, action: Action, observation: Observation, *, at: datetime) -> Outcome:
        """Seals a new draft only. Does not create a publish_jobs row or authority."""
        seal, fingerprint = _validated(action, observation)
        stamp = _ts(at)
        db = self._open()
        def transaction(db):
            if db.execute("SELECT 1 FROM r3_proposals WHERE source_run=? OR post_id=?",
                          (action.source_run, action.target_id)).fetchone():
                return Outcome("refused", "proposal_or_target_already_seen")
            db.execute("""INSERT INTO r3_proposals
                (source_run,post_id,draft_comment,seal_sha256,fingerprint,
                 snapshot_sha256,state,created_at,updated_at)
                VALUES(?,?,?,?,?,?,'proposed',?,?)""",
                (action.source_run, action.target_id, action.text, seal,
                 fingerprint, observation.snapshot_sha256, stamp, stamp))
            db.execute("INSERT INTO r3_lab_audit VALUES(NULL,?,?,?,?)",
                       (action.source_run, "propose", "sealed", stamp))
            return Outcome("proposed", "sealed_but_not_authorized")
        return self._finish(db, transaction)

    def queue(self, action: Action, observation: Observation, *, mode: str,
              at: datetime, policy: Policy | None = None) -> Outcome:
        """CAS sealed draft into the *same* synthetic legacy jobs DB.

        Manual: separately recorded exact owner approval of Bob-authored seal.
        Auto: separate r3 opt-in, legacy auto opt-in and new-v0.8 auto dial.
        Does not borrow v0.7 Scout approval, and never creates a real job.
        """
        seal, fingerprint = _validated(action, observation)
        stamp = _ts(at)
        if mode not in ("manual", "auto"):
            return Outcome("refused", "unsupported_mode")
        if policy is None:
            policy = Policy()
        db = self._open()
        def transaction(db):
            row = db.execute("SELECT post_id,seal_sha256,fingerprint,state "
                             "FROM r3_proposals WHERE source_run=?",
                             (action.source_run,)).fetchone()
            if row != (action.target_id, seal, fingerprint, "proposed"):
                return Outcome("refused", "unsealed_or_changed_draft")
            if db.execute("SELECT 1 FROM decisions WHERE run_id=?",
                          (action.source_run,)).fetchone():
                return Outcome("refused", "legacy_scout_run_collision")
            gate = self._permission(db, action, seal, mode, policy, at=at)
            if gate != "allow":
                return Outcome("refused", gate)
            if db.execute("SELECT 1 FROM publish_jobs WHERE run_id=? OR post_id=?",
                          (action.source_run, action.target_id)).fetchone():
                return Outcome("refused", "existing_legacy_target_or_job")
            if db.execute("SELECT 1 FROM publish_jobs WHERE post_id=? AND "
                          "(attempted_at IS NOT NULL OR state IN "
                          "('sending','uncertain','published','verifying'))",
                          (action.target_id,)).fetchone():
                return Outcome("refused", "legacy_target_attempted")
            db.execute("""INSERT INTO publish_jobs
                (run_id,approval_sha256,post_id,draft_comment,mode,state,
                 created_at,updated_at) VALUES(?,?,?,?,?,'queued',?,?)""",
                (action.source_run, seal, action.target_id, action.text,
                 mode, stamp, stamp))
            db.execute("UPDATE r3_proposals SET state='queued',updated_at=? "
                       "WHERE source_run=? AND state='proposed'",
                       (stamp, action.source_run))
            db.execute("INSERT INTO r3_lab_audit VALUES(NULL,?,?,?,?)",
                       (action.source_run, "queue_" + mode, "queued_simulated", stamp))
            return Outcome("queued_simulated", "sealed_new_draft_queued_in_lab")
        return self._finish(db, transaction)

    @staticmethod
    def _permission(db, action, seal, mode, policy, *, at):
        if not isinstance(policy, Policy) or policy.shadow:
            return "shadow_only"
        if policy.paused:
            return "v08_paused"
        dial = policy.dials.get("comment")
        if dial != ("auto" if mode == "auto" else "propose") and not (
                mode == "manual" and dial == "auto"):
            return "v08_comment_dial"
        # v0.8 pure check rejects malformed budgets. Counts below are
        # overridden with actual attempted_at before the simulated intent.
        disposition = check(action, PolicyState(at=_utc(at)), policy)
        if disposition.disposition != ("allow" if mode == "auto" else "propose") and not (
                mode == "manual" and disposition.disposition == "allow"):
            return "v08_" + disposition.reason
        if mode == "manual":
            approval = db.execute("SELECT seal_sha256,decision FROM r3_owner_approvals "
                                  "WHERE source_run=?", (action.source_run,)).fetchone()
            if approval != (seal, "approved"):
                return "owner_approval_missing_or_changed"
        else:
            consent = db.execute(
                "SELECT value FROM publish_settings WHERE name='r3_auto_enabled'").fetchone()
            legacy = db.execute(
                "SELECT value FROM publish_settings WHERE name='auto_enabled'").fetchone()
            if consent != ("1",) or legacy != ("1",):
                return "owner_auto_permission_off"
            if db.execute("SELECT 1 FROM decisions WHERE run_id=?",
                          (action.source_run,)).fetchone():
                return "legacy_owner_decision_overrides_auto"
            since = db.execute(
                "SELECT value FROM publish_settings WHERE name='r3_auto_since'").fetchone()
            # A new opt-in is NOT a permission to replay earlier Scout items.
            if not since or not isinstance(since[0], str):
                return "auto_since_missing"
            try:
                opt_in = _utc(datetime.fromisoformat(since[0].replace("Z", "+00:00")))
                original = datetime.strptime(action.source_run, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return "auto_since_invalid"
            if original <= opt_in:
                return "source_before_auto_opt_in"
        return "allow"

    def simulated_pre_send(self, action: Action, observation: Observation, *,
                           mode: str, at: datetime, policy: Policy | None = None,
                           paused: bool = True, proof: Proof | None = None) -> Outcome:
        """Atomic recheck and durable *synthetic* intent. Never POST."""
        seal, fingerprint = _validated(action, observation)
        stamp = _ts(at)
        if policy is None:
            policy = Policy()
        db = self._open()
        def transaction(db):
            row = db.execute(
                "SELECT state,post_id,draft_comment,seal_sha256,fingerprint,created_at "
                "FROM r3_proposals WHERE source_run=?", (action.source_run,)).fetchone()
            if row is None or row[0] != "queued":
                return Outcome("refused", "no_pending_r3_proposal")
            status, pid, body, stored_seal, stored_fingerprint, created = row
            if (pid, body, stored_seal, stored_fingerprint) != (
                    action.target_id, action.text, seal, fingerprint):
                return self._held(db, action.source_run, stamp, "sealed_payload_changed")
            job = db.execute(
                "SELECT mode,state,approval_sha256,post_id,draft_comment,attempted_at "
                "FROM publish_jobs WHERE run_id=?", (action.source_run,)).fetchone()
            if job != (mode, "queued", seal, pid, body, None):
                return self._held(db, action.source_run, stamp, "legacy_job_changed")
            gate = self._permission(db, action, seal, mode, policy, at=at)
            if gate != "allow":
                return self._held(db, action.source_run, stamp, gate)
            if type(paused) is not bool or paused:
                return self._held(db, action.source_run, stamp, "paused_or_unknown")
            if not isinstance(proof, Proof) or proof.post_id != pid:
                return Outcome("refused", "preflight_missing_or_wrong_target")
            try:
                proof_age = _utc(at) - _utc(proof.checked_at)
            except ValueError:
                return Outcome("refused", "preflight_clock_invalid")
            if proof_age < timedelta(0) or proof_age > timedelta(minutes=2):
                return Outcome("refused", "preflight_stale_or_future")
            if mode == "auto" and proof.friend_status != "clear":
                return self._held(db, action.source_run, stamp, "friend_guard_unproven")
            head = db.execute(
                "SELECT run_id FROM publish_jobs WHERE state='queued' "
                "ORDER BY CASE WHEN mode='manual' THEN 0 ELSE 1 END,"
                "created_at ASC,run_id ASC LIMIT 1").fetchone()
            if head != (action.source_run,):
                return Outcome("waiting", "legacy_manual_first_priority")
            if db.execute(
                "SELECT 1 FROM publish_jobs WHERE post_id=? AND run_id<>? "
                "AND (attempted_at IS NOT NULL OR state IN "
                "('sending','uncertain','published','verified_unconfirmed',"
                "'awaiting_verification','verifying','verification_expired',"
                "'sending_simulated')) LIMIT 1",
                (pid, action.source_run)).fetchone():
                return self._held(db, action.source_run, stamp, "target_already_attempted")
            try:
                source_at = datetime.strptime(action.source_run, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc)
                age = _utc(at) - source_at
            except ValueError:
                return self._held(db, action.source_run, stamp, "invalid_source_clock")
            if age < timedelta(0) or age > (timedelta(hours=3) if mode == "auto"
                                            else timedelta(days=7)):
                return self._held(db, action.source_run, stamp, "source_expired")
            try:
                allowed, _ = legacy_allowed(db, "comment", mode=mode, at=_utc(at))
                historical = attempts(db, "publish_jobs", _utc(at).strftime("%Y-%m-%d"))
                previous = last_attempt(db, "publish_jobs")
            except (ValueError, TypeError, sqlite3.Error):
                return self._held(db, action.source_run, stamp, "legacy_policy_invalid")
            if not allowed:
                return Outcome("waiting", "legacy_rate_or_budget")
            last = {"comment": previous} if previous else {}
            v08 = check(action, PolicyState(at=_utc(at),
                counts={"comment": historical}, last_action=last), policy)
            if (v08.disposition != ("allow" if mode == "auto" else "propose")
                    and not (mode == "manual" and v08.disposition == "allow")):
                if v08.reason in ("daily_budget", "minimum_spacing"):
                    return Outcome("waiting", "v08_rate_or_budget")
                return self._held(db, action.source_run, stamp, "v08_" + v08.reason)
            # There is exactly ONE counting ledger: legacy publish_jobs.
            # Durable synthetic intent and audit are in this same transaction.
            result = db.execute(
                "UPDATE publish_jobs SET state='sending_simulated',attempted_at=?,"
                "updated_at=? WHERE run_id=? AND mode=? AND state='queued'"
                " AND attempted_at IS NULL AND approval_sha256=? AND post_id=?"
                " AND draft_comment=?",
                (stamp, stamp, action.source_run, mode, seal, pid, body))
            if result.rowcount != 1:
                return self._held(db, action.source_run, stamp, "stale_legacy_cas")
            db.execute("UPDATE r3_proposals SET state='intent_simulated',updated_at=? "
                       "WHERE source_run=? AND state='queued'", (stamp, action.source_run))
            db.execute("INSERT INTO r3_lab_audit VALUES(NULL,?,?,?,?)",
                       (action.source_run, "intent_" + mode, "sending_simulated", stamp))
            return Outcome("intent_simulated", "one_counted_synthetic_intent")
        return self._finish(db, transaction)

    @staticmethod
    def _held(db, run, at, reason):
        db.execute("UPDATE r3_proposals SET state='held',updated_at=? "
                   "WHERE source_run=? AND state='queued'", (at, run))
        db.execute("UPDATE publish_jobs SET state='held_simulated',updated_at=? "
                   "WHERE run_id=? AND state='queued' AND attempted_at IS NULL", (at, run))
        db.execute("INSERT INTO r3_lab_audit VALUES(NULL,?,?,?,?)",
                   (run, "hold", reason, at))
        return Outcome("held", reason)

    def simulated_uncertain(self, run: str, *, at: datetime):
        if not isinstance(run, str) or not RUN.fullmatch(run):
            raise ValueError("invalid_lab_run")
        stamp = _ts(at)
        db = self._open()
        def transaction(db):
            job = db.execute("UPDATE publish_jobs SET state='uncertain',updated_at=? "
                "WHERE run_id=? AND state='sending_simulated' AND attempted_at IS NOT NULL",
                (stamp, run))
            if job.rowcount != 1:
                return Outcome("refused", "not_sending")
            db.execute("UPDATE r3_proposals SET state='uncertain_simulated',updated_at=? "
                       "WHERE source_run=? AND state='intent_simulated'", (stamp, run))
            db.execute("INSERT INTO r3_lab_audit VALUES(NULL,?,?,?,?)",
                       (run, "uncertain", "never_retry", stamp))
            return Outcome("uncertain_simulated", "never_retry")
        return self._finish(db, transaction)
