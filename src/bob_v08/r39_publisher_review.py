"""R3.9 publisher-side READ-ONLY admission review and fixed-host GET proof.

Development source only. This module is NOT imported by the installed v0.7
publisher. It neither acquires credentials nor inserts/claims queue jobs, and
no return value grants permission to POST. The credentialed publisher must
eventually own and revalidate the final pre-POST SQLite transaction.

Mockable HTTPS is supplied solely to let CI exercise the exact request parser
without touching Moltbook. Never accept an endpoint or URL from the agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import http.client
import json
from pathlib import Path
import sqlite3

from .core import Action, UUID
from .r3_cutover_rehearsal import verified_source, simulated_pause_state
from .r36_admission_contract import classify_draft
from .r37_trusted_gate_lab import _read_friends
from .r3_unified import _validated, _utc
from bob_activity_limits import allowed as legacy_allowed

HOST = "www.moltbook.com"
MAX_REMOTE_BYTES = 64 * 1024
GET_TIMEOUT_SECONDS = 6
PREFLIGHT_MAX_AGE = timedelta(minutes=2)


@dataclass(frozen=True)
class RemoteReview:
    matched: bool
    reason: str


@dataclass(frozen=True)
class AdmissionReview:
    status: str
    reason: str
    source_verified: bool = False
    owner_consent_observed: bool = False
    remote_target_verified: bool = False
    dispatch_authorized: bool = False
    acted: bool = False


def public_get_post(post_id: str, expected_author: str, *,
                    connection_factory=http.client.HTTPSConnection) -> RemoteReview:
    """Fetch exact public post via pinned HTTPS host; never follow redirects.

    Neither arbitrary paths nor response redirects are followed, and no bearer
    token, user-controlled HTTP host, cookies or response text are logged.
    """
    if (not isinstance(post_id, str) or not UUID.fullmatch(post_id)
            or not isinstance(expected_author, str)
            or not expected_author.strip() or len(expected_author) > 80):
        return RemoteReview(False, "invalid_preflight_identity")
    conn = None
    try:
        conn = connection_factory(HOST, timeout=GET_TIMEOUT_SECONDS)
        conn.request("GET", "/api/v1/posts/" + post_id, headers={
            "Accept": "application/json", "User-Agent": "BobR39PublisherReview/0.1"
        })
        response = conn.getresponse()
        if response.status != 200:
            return RemoteReview(False, "public_get_unavailable")
        # Read +1 to reject an oversized body; never echo the body to logs.
        raw = response.read(MAX_REMOTE_BYTES + 1)
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_REMOTE_BYTES:
            return RemoteReview(False, "invalid_preflight_body")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("success") is False:
            return RemoteReview(False, "invalid_preflight_response")
        nested = payload.get("data", payload)
        if not isinstance(nested, dict):
            return RemoteReview(False, "invalid_preflight_response")
        post = nested.get("post", nested)
        if not isinstance(post, dict) or post.get("id") != post_id:
            return RemoteReview(False, "target_identity_mismatch")
        if post.get("deleted") is True or post.get("is_deleted") is True:
            return RemoteReview(False, "target_deleted")
        author = post.get("author")
        if isinstance(author, dict):
            author = author.get("name", author.get("username"))
        if (not isinstance(author, str) or not author.strip()
                or author.casefold() != expected_author.casefold()):
            return RemoteReview(False, "author_identity_mismatch")
        return RemoteReview(True, "target_and_author_match")
    except (OSError, ValueError, TypeError, TimeoutError, RuntimeError,
            http.client.HTTPException):
        return RemoteReview(False, "public_get_error")
    finally:
        if conn is not None:
            try:
                conn.close()
            except (OSError, RuntimeError):
                pass


def _local_review(db: sqlite3.Connection, source_dir: Path, action: Action,
                  *, mode: str, at: datetime, pause_marker: Path):
    """Review exactly the original legacy queue and distinct R3 provenance.

    Every authority value is loaded from the supplied publisher-owned DB
    connection. Caller-provided model policies, friend-clear flags, approvals
    and preflight booleans are forbidden. This remains read-only.
    """
    if mode not in ("manual", "auto") or not isinstance(action, Action):
        return "invalid_review_mode", None
    if simulated_pause_state(pause_marker):
        return "paused_or_untrusted_marker", None
    try:
        observed, pin = verified_source(source_dir, action)
        origin = classify_draft(db, source_dir, action)
        if origin.origin != "r3_bob":
            return "not_a_new_sealed_bob_draft", None
        seal, fingerprint = _validated(action, observed)
        job = db.execute(
            "SELECT approval_sha256,post_id,draft_comment,mode,state,attempted_at "
            "FROM publish_jobs WHERE run_id=?", (action.source_run,)).fetchone()
        if job != (seal, action.target_id, action.text, mode, "queued", None):
            return "queued_job_changed", None
        approval = db.execute(
            "SELECT post_id,draft_comment,seal_sha256,fingerprint,"
            "snapshot_sha256,state FROM r3_proposals WHERE source_run=?",
            (action.source_run,)).fetchone()
        if approval != (action.target_id, action.text, seal,
                        fingerprint, pin.snapshot_sha256, "queued"):
            return "source_or_draft_seal_changed", None
        if db.execute(
                "SELECT 1 FROM decisions WHERE run_id=?",
                (action.source_run,)).fetchone():
            return "legacy_owner_decision_collision", None
        # If any other job could have reached the network for this post,
        # fail closed regardless of its current state (e.g. state='failed').
        if db.execute(
                "SELECT 1 FROM publish_jobs WHERE post_id=? AND run_id<>? "
                "AND (attempted_at IS NOT NULL OR state IN "
                "('sending','uncertain','published','verified_unconfirmed',"
                "'awaiting_verification','verifying','verification_expired',"
                "'verification_failed')) LIMIT 1",
                (action.target_id, action.source_run)).fetchone():
            return "duplicate_or_uncertain_target", None
        settings = dict(db.execute(
            "SELECT name,value FROM publish_settings WHERE name IN "
            "('auto_enabled','r3_auto_enabled','r3_auto_since','r3_comment_dial')"))
        dial = settings.get("r3_comment_dial")
        if dial not in ("propose", "auto"):
            return "owner_r3_dial_off", None
        if mode == "auto":
            if dial != "auto" or settings.get("auto_enabled") != "1" or (
                    settings.get("r3_auto_enabled") != "1"):
                return "separate_r3_auto_consent_required", None
            try:
                since = datetime.fromisoformat(
                    settings["r3_auto_since"].replace("Z", "+00:00"))
                since = _utc(since)
                from .core import RUN_ID
                if not RUN_ID.fullmatch(action.source_run):
                    raise ValueError("invalid source run")
                created = datetime.strptime(
                    action.source_run, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except (KeyError, TypeError, AttributeError, ValueError):
                return "auto_opt_in_unverified", None
            if created <= since:
                return "source_before_r3_auto_consent", None
            friend = _read_friends(db, source_dir, action, observed)
            if friend != "clear":
                return "friend_" + friend, None
        else:
            owner = db.execute(
                "SELECT seal_sha256,decision FROM r3_owner_approvals "
                "WHERE source_run=?", (action.source_run,)).fetchone()
            if owner != (seal, "approved"):
                return "new_bob_draft_approval_missing", None
        age = _utc(at) - datetime.strptime(
            action.source_run, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if age < timedelta(0) or age > (
                timedelta(hours=3) if mode == "auto" else timedelta(days=7)):
            return "source_expired_or_future", None
        head = db.execute(
            "SELECT run_id FROM publish_jobs WHERE state='queued' "
            "ORDER BY CASE WHEN mode='manual' THEN 0 ELSE 1 END,"
            "created_at ASC,run_id ASC LIMIT 1").fetchone()
        if head != (action.source_run,):
            return "manual_first_queue_priority", None
        allowed, _ = legacy_allowed(db, "comment", mode=mode, at=_utc(at))
        if not allowed:
            return "legacy_rate_or_budget", None
        if simulated_pause_state(pause_marker):
            return "paused_or_untrusted_marker", None
        return "reviewed", (pin, observed.author)
    except (ValueError, OSError, TypeError, KeyError, sqlite3.Error):
        return "local_review_unavailable", None


def review_publisher_admission(db: sqlite3.Connection, source_dir: Path,
                               action: Action, *, mode: str,
                               pause_marker: Path, clock, public_get=public_get_post
                               ) -> AdmissionReview:
    """Preflight a queued R3 comment, but NEVER authorize a send.

    Source/owner/queue/friend/pause/limits are read twice, bracketing a fixed
    HTTPS GET. The future real publisher must still perform an atomic
    pre-POST claim and a fresh host pause review; this deliberately does not.
    """
    if not callable(clock) or not callable(public_get):
        return AdmissionReview("refused", "trusted_clock_or_get_missing")
    try:
        before = _utc(clock())
    except (ValueError, TypeError):
        return AdmissionReview("refused", "invalid_review_clock")
    result, evidence = _local_review(
        db, source_dir, action, mode=mode, at=before, pause_marker=pause_marker)
    if evidence is None:
        return AdmissionReview("refused", result)
    pin, expected_author = evidence
    try:
        remote = public_get(action.target_id, expected_author)
        after = _utc(clock())
    except Exception:
        return AdmissionReview("refused", "public_get_error", source_verified=True,
                               owner_consent_observed=True)
    if not isinstance(remote, RemoteReview) or not remote.matched:
        reason = remote.reason if isinstance(remote, RemoteReview) else "invalid_remote_result"
        return AdmissionReview("refused", reason, source_verified=True,
                               owner_consent_observed=True)
    if after < before or after - before > PREFLIGHT_MAX_AGE:
        return AdmissionReview("refused", "preflight_clock_stale",
                               source_verified=True, owner_consent_observed=True)
    second, new_evidence = _local_review(
        db, source_dir, action, mode=mode, at=after, pause_marker=pause_marker)
    if new_evidence is None:
        return AdmissionReview("refused", "recheck_" + second, source_verified=True,
                               owner_consent_observed=True,
                               remote_target_verified=True)
    if new_evidence != evidence:
        return AdmissionReview("refused", "source_changed_during_get",
                               source_verified=True, owner_consent_observed=True,
                               remote_target_verified=True)
    return AdmissionReview(
        "reviewed", "needs_single_publisher_atomic_intent_and_final_pause",
        source_verified=True, owner_consent_observed=True,
        remote_target_verified=True,
        dispatch_authorized=False, acted=False)
