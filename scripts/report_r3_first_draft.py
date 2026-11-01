#!/usr/bin/env python3
"""Read-only, content-free first genuine R3 proposal readiness report.

Never creates owner approvals, queue rows, credentials, HTTP calls or services.
A passed report is NOT permission to publish a canary.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote


def summarize(state: dict, entries: list[dict]) -> dict:
    """Input entries must come from the source-seal-verifying owner reader."""
    ready = state.get("schema") == "ready"
    records = entries if ready else []
    proposed = [item for item in records if item.get("status") == "proposed"
                and item.get("approval") == "none"]
    approved = [item for item in records if item.get("status") == "proposed"
                and item.get("approval") == "approved"]
    queued = [item for item in records if item.get("queue_state") == "queued"
              and not item.get("attempted")]
    attempted = [item for item in records if item.get("attempted")]
    if not ready:
        next_gate = "stop_and_review_schema_or_host_boundary"
    elif attempted:
        next_gate = "reconcile_attempt_before_any_further_canary"
    elif queued:
        next_gate = "source_release_and_exact_one_attempt_review_required"
    elif approved:
        next_gate = "owner_may_queue_exact_reviewed_draft"
    elif proposed:
        next_gate = "owner_must_review_exact_draft_on_authenticated_r3_page"
    else:
        next_gate = "await_natural_proposed_decision"
    # Source run IDs are fixed-format metadata, not arbitrary untrusted text.
    selected = (queued or approved or proposed)
    return {
        "read_only": True,
        "public_canary_authorized": False,
        "schema_and_host_verified": ready,
        "manual_owner_mode": bool(state.get("manual")) if ready else False,
        "scope": "most_recent_20_source_verified_proposals_only",
        "verified_proposals": len(records),
        "unreviewed": len(proposed),
        "approved_not_queued": len(approved),
        "queued_unattempted": len(queued),
        "attempt_recorded": len(attempted),
        "candidate_run": selected[0]["run"] if selected else None,
        "next_gate": next_gate,
    }


def installed_report() -> dict:
    # The checkout supplies only read-only code; all Bob proposal decisions
    # are verified from the signed installed R3 package and fixed host paths.
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src" / "lib" / "bob"))
    from bob_r313d_package import load_verified
    load_verified()
    from bob_publish_common import DATA, DB
    from bob_r313d_owner import (
        trusted_manager_boundary, control_state, recent_proposals,
    )
    uri = "file:" + quote(str(DB), safe="/") + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, isolation_level=None,
                                 timeout=5)) as db:
        db.execute("PRAGMA query_only=ON")
        if not trusted_manager_boundary(db):
            return summarize({"schema": "unavailable"}, [])
        state = control_state(db)
        entries = recent_proposals(db, DATA, limit=20) if (
            state["schema"] == "ready") else []
        return summarize(state, entries)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="read-only local proposal inventory; never POST")
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("explicit --check is required")
    try:
        result = installed_report()
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error,
            ImportError):
        # Do not leak file locations, Scout text, raw model output or secrets.
        result = summarize({"schema": "unavailable"}, [])
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["schema_and_host_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
