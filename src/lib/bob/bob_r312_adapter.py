"""R3.12 source-only adapter for one existing credentialed publisher.

This module is intentionally imported by the *existing* publisher, but
R312_REAL_DISPATCH remains a hardcoded False. It never reads credentials,
performs HTTP, changes owner consent or claims an R3 job. All source kinds
share the same legacy publish_jobs queue. Missing/corrupt R3 tables fail
closed rather than accidentally interpreting Bob text as a legacy Scout draft.

The isolated fake-credentialed R3 POST harness lives in bob_v08 and cannot
be reached through a normal publisher timer invocation.
"""
from __future__ import annotations

import sqlite3

R312_REAL_DISPATCH = False
R312_VERSION = "r3.12-off-source-candidate"

LEGACY_QUEUE_HEAD = (
    "SELECT run_id,approval_sha256,post_id,draft_comment,mode,created_at "
    "FROM publish_jobs WHERE state='queued' "
    "ORDER BY CASE WHEN mode='manual' THEN 0 ELSE 1 END,"
    " created_at ASC, run_id ASC LIMIT 1"
)

NEW_QUEUE_HEAD = (
    "SELECT j.run_id,j.approval_sha256,j.post_id,j.draft_comment,j.mode,j.created_at "
    "FROM publish_jobs j WHERE j.state='queued' "
    "AND NOT EXISTS(SELECT 1 FROM r3_proposals p WHERE p.source_run=j.run_id) "
    "ORDER BY CASE WHEN j.mode='manual' THEN 0 ELSE 1 END,"
    " j.created_at ASC,j.run_id ASC LIMIT 1"
)


def _r3_present(db: sqlite3.Connection) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='r3_proposals'"
    ).fetchone()
    return row is not None


def _shape_ok(db: sqlite3.Connection) -> bool:
    """Strictly recognize the existing R3 proposal shape or fail closed."""
    columns = {r[1] for r in db.execute("PRAGMA table_info(r3_proposals)")}
    required = {
        "source_run", "post_id", "draft_comment", "seal_sha256", "fingerprint",
        "snapshot_sha256", "state", "created_at", "updated_at",
    }
    return required.issubset(columns)


def legacy_queue_head(db: sqlite3.Connection):
    """Select original Scout work while excluding R3 sealed proposal sources.

    With no additive table, execute the EXACT original legacy queue query.
    With an R3 table, a corrupt shape blocks the entire step before a POST.
    This does not promote R3 proposals to executable publication jobs.
    """
    if not _r3_present(db):
        return db.execute(LEGACY_QUEUE_HEAD).fetchone()
    if not _shape_ok(db):
        raise ValueError("r312_untrusted_proposal_schema")
    return db.execute(NEW_QUEUE_HEAD).fetchone()


def held_r3_count(db: sqlite3.Connection) -> int:
    """Read-only count; never reveal Bob's comment text in logs."""
    if not _r3_present(db):
        return 0
    if not _shape_ok(db):
        raise ValueError("r312_untrusted_proposal_schema")
    row = db.execute(
        "SELECT COUNT(*) FROM publish_jobs j JOIN r3_proposals p "
        "ON p.source_run=j.run_id WHERE j.state='queued'"
    ).fetchone()
    return int(row[0])


def candidate_dispatch_is_enabled(db: sqlite3.Connection) -> bool:
    """Always Off even when owner or legacy auto settings say otherwise.

    A separately reviewed release will have to remove this compile-time
    restriction and provide an authenticated, publisher-owned R3 send gate.
    Source-only acceptance is NEVER owner authorization to publish.
    """
    return R312_REAL_DISPATCH
