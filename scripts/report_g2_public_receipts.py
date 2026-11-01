#!/usr/bin/env python3
"""G2 read-only legacy comment receipt reconciliation; NEVER a cutover gate.

Reads the fixed private legacy SQLite queue with mode=ro and query_only.
Optional --public-get checks exact saved comment IDs on a fixed Moltbook HTTPS
GET endpoint using the existing bounded no-redirect visibility auditor.
Never reads Moltbook credentials, sends POST/PUT/PATCH/DELETE, prints content,
updates SQLite, changes units, or licenses v0.8 publication. Public listings
can be incomplete, and a known visible receipt cannot exclude a *second*
unrecorded remote post: external duplicate exclusion ALWAYS remains false.

This is a bounded assessment of the existing legacy COMMENT queue; original
post publication and other actors are outside this audit's scope.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import argparse
import json
import os
import pwd
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_comment_visibility as visibility

DB = Path.home() / ".config/moltbook/activity-queue.sqlite3"
MAX_JOBS = 40
SAFE_STATES = frozenset((
    "queued", "sending", "uncertain", "published", "failed", "verifying",
    "verified_unconfirmed", "awaiting_verification", "verification_expired",
    "needs_review", "expired", "cancelled", "verification_failed",
))
REQUIRED_COLUMNS = frozenset(
    ("run_id", "post_id", "comment_id", "state", "attempted_at"))


def _owner() -> bool:
    try:
        entry = pwd.getpwuid(os.geteuid())
        return (os.geteuid() != 0 and entry.pw_name == "openclaw"
                and entry.pw_dir == str(Path.home()))
    except (OSError, KeyError, ValueError):
        return False


def _snapshot(path: Path) -> tuple[int, list[tuple]]:
    """No metadata, source text, auth or other private tables leave this helper."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("unavailable_private_queue")
    if path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError("oversized_private_queue")
    with sqlite3.connect(path.absolute().as_uri() + "?mode=ro",
                         uri=True, timeout=4) as db:
        db.execute("PRAGMA query_only=ON")
        cols = {col[1] for col in db.execute("PRAGMA table_info(publish_jobs)")}
        if not REQUIRED_COLUMNS.issubset(cols):
            raise ValueError("unrecognized_legacy_queue_schema")
        count = db.execute(
            "SELECT COUNT(*) FROM publish_jobs WHERE attempted_at IS NOT NULL"
        ).fetchone()[0]
        rows = db.execute(
            "SELECT run_id,post_id,comment_id,state,attempted_at "
            "FROM publish_jobs WHERE attempted_at IS NOT NULL "
            "ORDER BY attempted_at,run_id LIMIT ?", (MAX_JOBS + 1,)
        ).fetchall()
        if type(count) is not int or count < 0:
            raise ValueError("invalid_legacy_attempt_count")
        return count, rows


def reconcile(path=DB, *, public_get=False, check=None) -> dict:
    """Return ONLY bounded aggregate counts; never certify no remote duplicates."""
    count, rows = _snapshot(path)
    truncated = count > MAX_JOBS or len(rows) > MAX_JOBS
    rows = rows[:MAX_JOBS]
    by_target = Counter()
    by_receipt = Counter()
    states = Counter()
    flagged = Counter()
    possible = []
    for run, post, receipt, state, attempted in rows:
        states[state if state in SAFE_STATES else "unrecognized"] += 1
        if (not isinstance(run, str) or not isinstance(attempted, str)
                or not attempted or not isinstance(post, str)
                or not visibility.UUID.fullmatch(post)):
            flagged["invalid_legacy_row"] += 1
        else:
            by_target[post] += 1
        if state not in SAFE_STATES:
            flagged["unrecognized_state"] += 1
        if state in ("sending", "uncertain", "verification_failed"):
            flagged["unresolved_attempt_state"] += 1
        if isinstance(receipt, str) and visibility.UUID.fullmatch(receipt):
            by_receipt[receipt] += 1
            if isinstance(post, str) and visibility.UUID.fullmatch(post):
                possible.append((post, receipt))
            else:
                flagged["receipt_without_valid_post"] += 1
        else:
            flagged["missing_or_invalid_receipt_id"] += 1
    flagged["repeat_attempted_target_groups"] = sum(
        num > 1 for num in by_target.values())
    flagged["reused_comment_receipt_ids"] = sum(
        num > 1 for num in by_receipt.values())
    observations = Counter()
    if public_get:
        lookup = check if check is not None else visibility.audit_one
        if not callable(lookup):
            raise ValueError("unreviewed_public_get_provider")
        for post, receipt in possible:
            try:
                # Existing auditor enforces fixed host, UUID-only paths,
                # no redirects, bounded response/pages and GET-only.
                result = lookup(post, receipt, max_pages=2)
            except (OSError, ValueError, TypeError, TimeoutError):
                result = "public_check_unavailable"
            if result not in (
                "visible_in_public_listing", "not_observed_in_public_listing",
                "scan_incomplete", "public_check_unavailable", "id_unconfirmed"):
                result = "public_check_unavailable"
            observations[result] += 1
    stable = True
    if public_get:
        try:
            second_count, second_rows = _snapshot(path)
            stable = (second_count == count and
                      second_rows == (rows if not truncated else rows + []))
            # If truncated, cannot safely compare all selected rows after an
            # intervening writer, and should never claim a complete audit.
            if truncated:
                stable = False
        except (OSError, ValueError, sqlite3.Error):
            stable = False
    all_receipts_visible = bool(
        public_get and stable and not truncated and count > 0
        and len(possible) == count
        and observations["visible_in_public_listing"] == count
        and not any(flagged.values())
    )
    return {
        "format": "bob-g2-public-receipt-reconciliation-v1",
        "authority": "read_only_legacy_comment_audit",
        "attempts_total": count,
        "attempts_inspected": len(rows),
        "attempts_truncated": truncated,
        "db_unchanged_during_get": stable if public_get else "not_checked",
        "attempted_state_counts": dict(sorted(states.items())),
        "local_review_flags": dict(sorted(flagged.items())),
        "saved_receipt_ids": len(possible),
        "public_get_enabled": bool(public_get),
        "public_observation_counts": dict(sorted(observations.items())),
        "known_receipts_all_visible": all_receipts_visible,
        "status": ("known_receipts_visible" if all_receipts_visible
                   else "review_required"),
        "external_duplicate_posting_excluded": False,
        "original_posts_audited": False,
        "credentials_loaded": False,
        "external_write_requests": 0,
        "database_or_systemd_changed": False,
        "r3_real_publishing_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-get", action="store_true",
                        help="explicit opt-in to bounded anonymous Moltbook HTTPS GETs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not _owner():
        print("G2 RECEIPTS REFUSED: expected normal openclaw account")
        return 1
    try:
        result = reconcile(public_get=args.public_get)
    except (OSError, ValueError, TypeError, sqlite3.Error):
        print("G2 RECEIPTS REFUSED: private read-only queue unavailable")
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("G2 LEGACY COMMENT RECEIPTS (READ ONLY)")
        for label, key in (
            ("historical attempts", "attempts_total"),
            ("attempts inspected", "attempts_inspected"),
            ("scope truncated", "attempts_truncated"),
            ("saved receipt IDs", "saved_receipt_ids"),
            ("local review flags", "local_review_flags"),
            ("public GET requested", "public_get_enabled"),
            ("public observations", "public_observation_counts"),
            ("database stable during GET", "db_unchanged_during_get"),
            ("known receipts all visible", "known_receipts_all_visible"),
            ("receipt reconciliation", "status"),
        ):
            print(label + ":", result[key])
        print("External duplicate publishing conclusively excluded: NO")
        print("Original-post history audited: NO")
        print("Credentials, database, services or publishing state changed: NO")
        print("R3 real publishing authorized: NO")
    # 'review_required' can be a truthful completed audit, not a CLI failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
