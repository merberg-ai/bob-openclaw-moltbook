"""R3.6 source-kind classifier for a FUTURE single publisher.

This is intentionally read-only and never sends or admits a live job.
The legacy publisher only handles exact existing Scout drafts. New Bob text
must instead match an independent sealed proposal in the SAME queue schema.
Actual production owner, friend, GET, pause, and dispatch checks are NOT here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import sqlite3

from .core import Action
from .r3_cutover_rehearsal import verified_source
from .r3_unified import _validated


@dataclass(frozen=True)
class OriginReview:
    origin: str
    reason: str
    source_verified: bool
    dispatch_authorized: bool = False


def classify_draft(db: sqlite3.Connection, source_dir: Path, action: Action) -> OriginReview:
    """Read-only exact-source/origin test, not a sending authorization check."""
    try:
        observation, pin = verified_source(source_dir, action)
        new_seal, fingerprint = _validated(action, observation)
    except (ValueError, OSError, TypeError):
        return OriginReview("refused", "saved_scout_source_unverified", False)
    try:
        job = db.execute(
            "SELECT approval_sha256,post_id,draft_comment,mode,state,attempted_at "
            "FROM publish_jobs WHERE run_id=?", (action.source_run,)).fetchone()
        if job is None:
            return OriginReview("refused", "no_exact_queued_job", True)
        digest, pid, draft, mode, state, attempted = job
        if (pid != action.target_id or draft != action.text
                or mode not in ("manual", "auto") or state != "queued"
                or attempted is not None):
            return OriginReview("refused", "job_changed_or_not_pending", True)
        # The source-validated original Scout draft can only use the legacy
        # path if the original approval digest validates THIS exact text.
        if digest == pin.scout_approval_sha256:
            expected = hashlib.sha256(
                (pid + "\n" + draft + "\n" + pin.snapshot_sha256).encode("utf-8")
            ).hexdigest()
            if expected != digest:
                return OriginReview("refused", "scout_draft_not_exact", True)
            return OriginReview("legacy_scout", "use_existing_v07_validator", True)
        if digest != new_seal:
            return OriginReview("refused", "unrecognized_seal", True)
        # Never infer Bob origin from a syntactically valid SHA alone.
        # Only the additive R3 proposal with exact fingerprint qualifies.
        present = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='r3_proposals'").fetchone()
        if not present:
            return OriginReview("refused", "new_comment_without_origin_record", True)
        linked = db.execute(
            "SELECT post_id,draft_comment,seal_sha256,fingerprint,"
            "snapshot_sha256,state FROM r3_proposals WHERE source_run=?",
            (action.source_run,)).fetchone()
        if linked != (
                pid, draft, new_seal, fingerprint,
                pin.snapshot_sha256, "queued"):
            return OriginReview("refused", "new_comment_origin_changed", True)
        return OriginReview("r3_bob", "origin_verified_requires_publisher_gate", True)
    except sqlite3.Error:
        return OriginReview("refused", "queue_schema_or_query_unavailable", True)
