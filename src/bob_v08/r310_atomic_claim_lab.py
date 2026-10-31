"""R3.10 SINGLE-PUBLISHER ATOMIC CLAIM LAB: NO CREDENTIALS OR POST.

Rehearses the publisher-owned transition that is missing from R3.9: after a
verified two-pass source/owner/GET review, the same legacy-shaped publish_jobs
table is claimed under BEGIN IMMEDIATE with a fresh owner/queue/source check.

This is NOT wired into the credentialed v0.7 publisher. The only accepted DB
is the marked, private R3.3 synthetic fixture. Its sibling 'scout' directory
and 'paused' marker are fixed by layout, not selected by model or caller.
Every result is simulated, acted=False, dispatch_authorized=False.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

from .core import Action
from .r3_unified import UnifiedLab, _utc, _ts, _validated
from .r3_cutover_rehearsal import verified_source, simulated_pause_state
from .r39_publisher_review import (
    _local_review, review_publisher_admission, RemoteReview, PREFLIGHT_MAX_AGE,
)

@dataclass(frozen=True)
class ClaimResult:
    state: str
    reason: str
    simulated: bool = True
    acted: bool = False
    dispatch_authorized: bool = False
    attempted_at_recorded: bool = False


def _fixture_ro(lab: UnifiedLab) -> sqlite3.Connection:
    """Open ONLY a verified marked fixture for the preflight read."""
    guard = lab._open()
    guard.rollback()
    guard.close()
    uri = lab.path.absolute().as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=4)
    db.execute("PRAGMA query_only=ON")
    return db


def _atomic_claim(db: sqlite3.Connection, action: Action, mode: str,
                  seal: str, fingerprint: str, snapshot: str,
                  stamp: str) -> int:
    """Single exactly matched update; all authority in locked local SQLite.

    Source/friend/pause are validated in the same caller-owned critical section,
    but they are FILESYSTEM state: a future live publisher also needs a final
    pre-POST barrier after committing its durable intent.
    """
    if mode not in ("manual", "auto"):
        return 0
    # SQL owner constraints rechecked at claim, as defense in depth. These
    # settings default Off when missing; the old v0.7 auto bit is insufficient.
    if mode == "auto":
        consent = (
            "EXISTS(SELECT 1 FROM publish_settings WHERE name='auto_enabled' AND value='1')"
            " AND EXISTS(SELECT 1 FROM publish_settings WHERE name='r3_auto_enabled' AND value='1')"
            " AND EXISTS(SELECT 1 FROM publish_settings WHERE name='r3_comment_dial' AND value='auto')"
            " AND NOT EXISTS(SELECT 1 FROM decisions WHERE run_id=publish_jobs.run_id)"
        )
    else:
        consent = (
            "EXISTS(SELECT 1 FROM publish_settings WHERE name='r3_comment_dial'"
            " AND value IN ('propose','auto'))"
            " AND EXISTS(SELECT 1 FROM r3_owner_approvals a WHERE "
            "a.source_run=publish_jobs.run_id AND a.seal_sha256=publish_jobs.approval_sha256 "
            "AND a.decision='approved')"
        )
    sql = (
        "UPDATE publish_jobs SET state='sending_simulated',attempted_at=?,updated_at=? "
        "WHERE run_id=? AND mode=? AND state='queued' AND attempted_at IS NULL "
        "AND approval_sha256=? AND post_id=? AND draft_comment=? "
        "AND EXISTS(SELECT 1 FROM r3_proposals p "
        "WHERE p.source_run=publish_jobs.run_id AND p.post_id=publish_jobs.post_id "
        "AND p.draft_comment=publish_jobs.draft_comment "
        "AND p.seal_sha256=publish_jobs.approval_sha256 "
        "AND p.fingerprint=? AND p.snapshot_sha256=? AND p.state='queued') "
        "AND " + consent
    )
    return db.execute(sql, (stamp, stamp, action.source_run, mode, seal,
                            action.target_id, action.text,
                            fingerprint, snapshot)).rowcount


def rehearse_atomic_claim(lab: UnifiedLab, action: Action, *, mode: str,
                          clock, public_get, before_claim=None) -> ClaimResult:
    """Two-pass R3.9 review, then a fresh final BEGIN IMMEDIATE claim.

    public_get/clock/before_claim are TEST HARNESS INJECTIONS. There is no
    built-in HTTP transport. A real publisher would need a trusted clock,
    private root and fixed-host GET source, plus an authorized dispatch adapter.
    """
    if type(lab) is not UnifiedLab or type(action) is not Action:
        return ClaimResult("refused", "invalid_synthetic_claim")
    if mode not in ("manual", "auto") or not callable(clock) or not callable(public_get):
        return ClaimResult("refused", "invalid_claim_inputs")
    # Derive both filesystem references from the already marked private lab.
    root = lab.path.parent.parent
    source_dir = root / "scout"
    pause_marker = root / "paused"
    try:
        db = _fixture_ro(lab)
        try:
            if source_dir.is_symlink() or not source_dir.is_dir() or (
                    source_dir.stat().st_mode & 0o077):
                return ClaimResult("refused", "untrusted_fixed_source_root")
            original, pinned = verified_source(source_dir, action)
            seal, fingerprint = _validated(action, original)
            begin = _utc(clock())
            review = review_publisher_admission(
                db, source_dir, action, mode=mode, pause_marker=pause_marker,
                clock=clock, public_get=public_get)
        finally:
            db.close()
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return ClaimResult("refused", "preflight_unavailable")
    if review.status != "reviewed" or not (
            review.source_verified and review.owner_consent_observed
            and review.remote_target_verified):
        return ClaimResult("refused", "review_" + review.reason)
    if before_claim is not None:
        # Fault-injection hook, not a host permission input.
        if not callable(before_claim):
            return ClaimResult("refused", "invalid_test_hook")
        before_claim()
    try:
        at = _utc(clock())
    except (ValueError, TypeError):
        return ClaimResult("refused", "claim_clock_unavailable")
    if at < begin or at - begin > PREFLIGHT_MAX_AGE:
        return ClaimResult("refused", "claim_preflight_expired")
    try:
        db = lab._open()  # BEGIN IMMEDIATE serializes the single legacy queue.
    except (OSError, ValueError, sqlite3.Error):
        return ClaimResult("refused", "synthetic_writer_unavailable")
    try:
        # No model-supplied policy, consent, proof, source path or pause state
        # enters the claim. The publisher re-derives them from fixed sources.
        observed, current = verified_source(source_dir, action, pinned=pinned)
        if current != pinned:
            db.rollback()
            return ClaimResult("refused", "source_drift_at_claim")
        current_seal, current_fingerprint = _validated(action, observed)
        if (current_seal, current_fingerprint) != (seal, fingerprint):
            db.rollback()
            return ClaimResult("refused", "text_or_origin_drift_at_claim")
        review_reason, details = _local_review(
            db, source_dir, action, mode=mode, at=at, pause_marker=pause_marker)
        if details != (pinned, observed.author):
            db.rollback()
            return ClaimResult("refused", "final_" + review_reason)
        if simulated_pause_state(pause_marker):
            db.rollback()
            return ClaimResult("refused", "paused_at_atomic_claim")
        stamp = _ts(at)
        changed = _atomic_claim(db, action, mode, seal, fingerprint,
                                pinned.snapshot_sha256, stamp)
        if changed != 1:
            db.rollback()
            return ClaimResult("refused", "stale_claim_cas")
        proposed = db.execute(
            "UPDATE r3_proposals SET state='intent_simulated',updated_at=? "
            "WHERE source_run=? AND state='queued' AND seal_sha256=? "
            "AND fingerprint=? AND snapshot_sha256=?",
            (stamp, action.source_run, seal, fingerprint,
             pinned.snapshot_sha256))
        if proposed.rowcount != 1:
            db.rollback()
            return ClaimResult("refused", "stale_proposal_cas")
        db.execute(
            "INSERT INTO r3_lab_audit VALUES(NULL,?,?,?,?)",
            (action.source_run, "r310_claim", "one_counted_simulated_intent", stamp))
        db.commit()
    except (OSError, ValueError, TypeError, sqlite3.Error):
        db.rollback()
        return ClaimResult("refused", "atomic_claim_failed")
    finally:
        db.close()

    # An FS pause or source revocation after COMMIT cannot roll back an
    # externally possible POST. Conservatively lock the consumed attempt.
    try:
        post_claim_safe = (
            not simulated_pause_state(pause_marker)
            and verified_source(source_dir, action, pinned=pinned)[1] == pinned)
    except (OSError, ValueError, TypeError):
        post_claim_safe = False
    if not post_claim_safe:
        lab.simulated_uncertain(action.source_run, at=at)
        return ClaimResult("uncertain_simulated",
                           "post_intent_source_or_pause_changed", attempted_at_recorded=True)
    # Not a dispatch token. Re-use R3.8's inert sink only in a separate test;
    # no network callback or live publisher import is reachable from here.
    return ClaimResult("claimed_simulated", "one_atomic_counted_intent_only",
                       attempted_at_recorded=True)
