"""R3.2: legacy publisher COMPATIBILITY LAB, never a live publisher.

Runs one atomic simulated 'sending' transition against a *synthetic fixture*
of the exact v0.7 queue schema. Reuses the reviewed v0.7 activity_allowed()
implementation rather than copying rate-limit logic. No network, credentials,
source file discovery, web endpoints, service changes, or deployed entrypoint.

The actual v0.7 publisher remains the only credentialed real writer. Nothing
here is authorized to run against ~/.config/moltbook/activity-queue.sqlite3.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys

from .core import Action, Observation, parse_decision

LAB_DIR = "r3-compat-fixtures"
LAB_DB = "r3-legacy-compat-lab.sqlite3"
LAB_MARKER = "r3-legacy-compat-synthetic-only-v1"
# Source review: src/bin/bob-moltbook-publisher (manual-first and age checks).
LOCKING_STATES = ("sending", "uncertain", "published", "verified_unconfirmed",
                  "awaiting_verification", "verifying", "verification_expired")
RUN_ID = re.compile(r"[0-9]{8}T[0-9]{6}Z\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")

# These imports only expose the shared policy evaluator. Never call
# bob_publish_common.connect(), whose default path is the real legacy DB.
LIB = str(Path(__file__).resolve().parents[1] / "lib" / "bob")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
from bob_activity_limits import allowed as v07_activity_allowed  # noqa: E402


@dataclass(frozen=True)
class CompatResult:
    state: str
    reason: str
    simulated: bool = True
    acted: bool = False


def _stamp(at: datetime) -> str:
    if (not isinstance(at, datetime) or at.tzinfo is None
            or at.utcoffset() is None):
        raise ValueError("invalid_utc_clock")
    return at.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _decision_is_source_bound(action: Action, observed: Observation) -> bool:
    if (not isinstance(action, Action) or not isinstance(observed, Observation)
            or not isinstance(observed.snapshot_sha256, str)
            or not HASH.fullmatch(observed.snapshot_sha256)
            or not isinstance(observed.approval_sha256, str)
            or not HASH.fullmatch(observed.approval_sha256)):
        return False
    # We validate the original Action with the strict canonical model contract,
    # not merely source/target field equality.
    import json
    payload = json.dumps(dict(type=action.kind, source_run=action.source_run,
                              target_id=action.target_id, reason=action.reason,
                              text=action.text), ensure_ascii=True)
    try:
        return parse_decision(payload, observed) == action and action.kind == "comment"
    except (TypeError, ValueError):
        return False


class LegacyCompatLab:
    """Hard-bound to an owner-private, lab-marker-protected fixture database."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _open(self) -> sqlite3.Connection:
        p = self.path
        # Never access a production database even when someone passes its path.
        if p.name != LAB_DB or p.parent.name != LAB_DIR:
            raise ValueError("not_a_compat_lab_path")
        if (p.is_symlink() or p.parent.is_symlink()
                or not p.is_file() or not p.parent.is_dir()
                or p.stat().st_mode & 0o077 or p.parent.stat().st_mode & 0o077):
            raise ValueError("unsafe_compat_lab_fixture")
        db = sqlite3.connect(p, isolation_level=None, timeout=4)
        try:
            db.execute("PRAGMA busy_timeout=4000")
            db.execute("BEGIN IMMEDIATE")
            marker = db.execute("SELECT value FROM r3_lab_meta WHERE name='contract'").fetchone()
            if marker != (LAB_MARKER,):
                raise ValueError("incorrect_compat_lab_marker")
            return db
        except BaseException:
            db.rollback()
            db.close()
            raise

    def simulated_claim(self, action: Action, observed: Observation, *,
                        at: datetime, paused: bool = True,
                        preflight_verified: bool = False,
                        friend_status: str = "unknown") -> CompatResult:
        """Compare exact queued draft + approval, then simulate sending atomically.

        Positive status marks 'sending_simulated' only in the disposable fixture.
        Never imports API, reads a key or calls a publisher; never changes live
        queue schema. External friend/GET status cannot be inferred here.
        """
        if not _decision_is_source_bound(action, observed):
            return CompatResult("refused", "model_or_source_unverified")
        timestamp = _stamp(at)
        if type(paused) is not bool or type(preflight_verified) is not bool:
            return CompatResult("refused", "missing_owner_or_preflight_state")
        db = self._open()
        try:
            head = db.execute(
                "SELECT run_id,approval_sha256,post_id,draft_comment,mode,created_at "
                "FROM publish_jobs WHERE state='queued' "
                "ORDER BY CASE WHEN mode='manual' THEN 0 ELSE 1 END, "
                "created_at ASC,run_id ASC LIMIT 1").fetchone()
            if head is None:
                result = CompatResult("refused", "no_queued_job")
            else:
                run, digest, post, draft, mode, created = head
                if (run, post) != (action.source_run, action.target_id):
                    result = CompatResult("refused", "manual_first_queue_head")
                elif (digest != observed.approval_sha256 or
                      draft != action.text or
                      not isinstance(draft, str) or not draft.strip()):
                    # The independent R2 model may propose a different comment
                    # from the v0.7 Scout draft. Never silently substitute it.
                    result = CompatResult("refused", "draft_or_source_changed")
                elif mode not in ("manual", "auto"):
                    result = CompatResult("refused", "invalid_job_mode")
                elif paused:
                    result = CompatResult("refused", "global_pause")
                elif not preflight_verified:
                    result = CompatResult("refused", "preflight_unverified")
                else:
                    result = self._check_and_mark(
                        db, action, run, digest, post, draft, mode, timestamp,
                        friend_status)
            # One transaction includes selecting queue order, policy/approval
            # read, attempted_at CAS and sanitized audit event, if eligible.
            db.commit()
            return result
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _check_and_mark(db, action, run, digest, post, draft, mode,
                        timestamp, friend_status):
        if mode == "auto":
            setting = db.execute(
                "SELECT value FROM publish_settings WHERE name='auto_enabled'").fetchone()
            if not setting or setting[0] != "1":
                return CompatResult("refused", "auto_disabled")
            if db.execute("SELECT 1 FROM decisions WHERE run_id=?", (run,)).fetchone():
                return CompatResult("refused", "owner_decision_overrides_auto")
            if friend_status != "clear":
                # Real publisher applies allow_auto_candidate() using verified
                # friend data; unknown is not permission.
                return CompatResult("refused", "friend_review_unproven")
        else:
            row = db.execute(
                "SELECT draft_sha256,status FROM decisions WHERE run_id=?",
                (run,)).fetchone()
            if row != (digest, "approved"):
                return CompatResult("refused", "manual_approval_missing_or_changed")

        try:
            when = datetime.strptime(run, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            now = datetime.fromisoformat(timestamp)
        except (ValueError, TypeError):
            return CompatResult("refused", "invalid_source_clock")
        age = now - when
        if age < timedelta(0) or age > (timedelta(hours=3) if mode == "auto"
                                         else timedelta(days=7)):
            return CompatResult("refused", "draft_expired_or_future")

        duplicate = db.execute(
            "SELECT 1 FROM publish_jobs WHERE post_id=? AND run_id<>? "
            "AND (attempted_at IS NOT NULL OR state IN "
            "('sending','uncertain','published','verified_unconfirmed',"
            "'awaiting_verification','verifying','verification_expired')) LIMIT 1",
            (post, run)).fetchone()
        if duplicate is not None:
            return CompatResult("refused", "duplicate_or_uncertain_target")
        # The *actual* existing shared policy, reading real fixture settings
        # and attempted_at from the same BEGIN IMMEDIATE transaction.
        try:
            eligible, _ = v07_activity_allowed(
                db, "comment", mode=mode, at=now)
        except (ValueError, TypeError, sqlite3.Error):
            return CompatResult("refused", "invalid_legacy_budget")
        if not eligible:
            return CompatResult("refused", "legacy_budget_or_spacing")
        # Exact source/approval/action CAS equivalent to the old publisher,
        # except synthetic state name and zero possibility of network send.
        decision_clause = (
            "EXISTS(SELECT 1 FROM decisions d WHERE d.run_id=publish_jobs.run_id "
            "AND d.draft_sha256=publish_jobs.approval_sha256 "
            "AND d.status='approved')" if mode == "manual" else
            "NOT EXISTS(SELECT 1 FROM decisions d WHERE d.run_id=publish_jobs.run_id)")
        )
        changed = db.execute(
            "UPDATE publish_jobs SET state='sending_simulated',"
            "attempted_at=?,updated_at=? "
            "WHERE run_id=? AND post_id=? AND mode=? AND approval_sha256=? "
            "AND draft_comment=? AND state='queued' AND attempted_at IS NULL "
            "AND " + decision_clause,
            (timestamp, timestamp, run, post, mode, digest, draft))
        if changed.rowcount != 1:
            return CompatResult("refused", "stale_queue_claim")
        db.execute(
            "INSERT INTO r3_lab_audit(run_id,kind,transition,at_utc) "
            "VALUES(?,?,?,?)",
            (run, mode, "sending_simulated", timestamp))
        return CompatResult("intent_simulated", "legacy_checks_passed")

    def simulated_uncertain(self, run_id: str, *, at: datetime) -> CompatResult:
        """Synthetic restart/crash path, leaves attempted_at and target locked."""
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise ValueError("invalid_source_run")
        stamp = _stamp(at)
        db = self._open()
        try:
            row = db.execute(
                "UPDATE publish_jobs SET state='uncertain',updated_at=? "
                "WHERE run_id=? AND state='sending_simulated' AND attempted_at IS NOT NULL",
                (stamp, run_id))
            if row.rowcount != 1:
                result = CompatResult("refused", "uncertain_transition_denied")
            else:
                db.execute(
                    "INSERT INTO r3_lab_audit(run_id,kind,transition,at_utc) "
                    "VALUES(?,?,?,?)", (run_id, "unknown", "uncertain", stamp))
                result = CompatResult("uncertain_simulated", "never_auto_retry")
            db.commit()
            return result
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
