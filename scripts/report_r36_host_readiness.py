#!/usr/bin/env python3
"""R3.6 on-host READ-ONLY compatibility report, never a production cutover.

Outputs only allowlisted service states, queue table/column names, bounded
counts and policy categories. Does not read secrets, raw comments, agent prompts,
journal entries, Environment/ExecStart values, Windows startup files or API keys.
Does not create/modify databases, enable units, touch settings or make HTTP calls.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

from report_r3_cutover_inventory import (
    QUEUE, PAUSED, UNITS, queue_facts, unit_facts,
)

REQUIRED = {
    "publish_jobs": frozenset((
        "run_id", "approval_sha256", "post_id", "draft_comment", "mode", "state",
        "created_at", "attempted_at", "comment_id", "updated_at")),
    "decisions": frozenset(("run_id", "draft_sha256", "status", "decided_at")),
    "publish_settings": frozenset(("name", "value")),
    "publish_events": frozenset(("id", "at", "kind", "details")),
    "published_replies": frozenset((
        "id", "post_id", "comment_id", "detected_at")),
}
# These candidate tables must NOT be assumed to exist in today's live queue.
ADDITIVE = frozenset((
    "r3_proposals", "r3_owner_approvals", "r3_lab_audit", "r35_schema_meta"))
UNCERTAIN = frozenset((
    "sending", "uncertain", "verified_unconfirmed", "verifying",
    "verification_expired", "awaiting_verification", "verification_failed"))
CRITICAL = (
    ("user", "bob-moltbook-publisher.timer"),
    ("user", "bob-moltbook-publisher.service"),
    ("user", "bob-startup-reconcile.timer"),
    ("user", "bob-v08-shadow.timer"),
    ("user", "bob-r3-candidate-publisher.timer"),
    ("user", "bob-r3-candidate-publisher.service"),
    ("system", "bob-moltbook-scout.timer"),
)
SAFE_UNIT_KEYS = {"scope", "unit", "load", "active", "sub", "enabled", "result"}


def queue_schema(path: Path = QUEUE) -> dict:
    """PRAGMA read-only and fixed-name COUNT() against a consistent snapshot."""
    result = {
        "status": "unavailable", "legacy_contract": "unverified",
        "tables_present": [], "tables_missing": [],
        "additive_tables_present": [], "rows": {},
        "uncertain_jobs": None, "attempted_jobs": None,
    }
    p = Path(path)
    try:
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 256 * 1024 * 1024:
            return result
        # SQLite URI mode=ro does not create a new DB. Do NOT use immutable=1:
        # this must see the latest committed WAL state.
        with closing(sqlite3.connect(p.absolute().as_uri() + "?mode=ro",
                                    uri=True, timeout=2)) as con:
            con.execute("PRAGMA query_only=ON")
            con.execute("BEGIN")
            table_names = {
                row[0] for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('publish_jobs','decisions','publish_settings',"
                    "'publish_events','published_replies','r3_proposals','r3_owner_approvals',"
                    "'r3_lab_audit','r35_schema_meta')")}
            failures = []
            for name, expected in REQUIRED.items():
                if name not in table_names:
                    failures.append(name)
                    continue
                # name is a literal from our own constant mapping.
                cols = {str(row[1]) for row in con.execute(
                    'PRAGMA table_info("' + name + '")')}
                if not expected.issubset(cols):
                    failures.append(name)
            counts = {}
            for name in ("publish_jobs", "decisions", "publish_events", "published_replies"):
                if name in table_names:
                    counts[name] = int(con.execute(
                        'SELECT COUNT(*) FROM "' + name + '"').fetchone()[0])
            if "publish_jobs" in table_names and "publish_jobs" not in failures:
                attempted = int(con.execute(
                    "SELECT COUNT(*) FROM publish_jobs "
                    "WHERE attempted_at IS NOT NULL").fetchone()[0])
                uncertainty = int(con.execute(
                    "SELECT COUNT(*) FROM publish_jobs WHERE state IN "
                    "('sending','uncertain','verified_unconfirmed','verifying',"
                    "'verification_expired','awaiting_verification',"
                    "'verification_failed')").fetchone()[0])
            else:
                attempted, uncertainty = None, None
            result.update(
                status="ok", legacy_contract="match" if not failures else "mismatch",
                tables_present=sorted(table_names & REQUIRED.keys()),
                tables_missing=sorted(failures),
                additive_tables_present=sorted(table_names & ADDITIVE),
                rows=counts, attempted_jobs=attempted, uncertain_jobs=uncertainty,
            )
            con.rollback()
    except (OSError, ValueError, sqlite3.Error):
        pass
    return result


def review(*, queue_path: Path = QUEUE, paused_path: Path = PAUSED,
           unit_reader=unit_facts, queue_reader=queue_facts,
           schema_reader=queue_schema) -> dict:
    """Sanitized, finite report. No host switch or publisher grant is possible."""
    units = [unit_reader(scope, name) for scope, name in UNITS]
    # Force small, finite fixed service metadata. Provider text is never echoed.
    checked = []
    for expected, record in zip(UNITS, units):
        if not isinstance(record, dict):
            record = {}
        checked.append({
            key: (record.get(key) if key in ("scope", "unit") and
                  record.get(key) == expected[i] else
                  record.get(key) if key in SAFE_UNIT_KEYS and
                  isinstance(record.get(key), str) and
                  record.get(key) in _allowed_field(key) else "unknown")
            for i, key in enumerate(("scope", "unit", "load", "active",
                                     "sub", "enabled", "result"))
        })
    # Existing reader itself emits only validated settings/counts.
    q = queue_reader(queue_path, paused=paused_path)
    shape = schema_reader(queue_path)
    by_name = {(r["scope"], r["unit"]): r for r in checked}
    pub = by_name.get(("user", "bob-moltbook-publisher.timer"), {})
    candidate = [by_name.get(("user", name), {}) for name in
                 ("bob-r3-candidate-publisher.timer",
                  "bob-r3-candidate-publisher.service")]
    blockers = []
    if pub.get("active") != "active":
        blockers.append("legacy_publisher_timer_not_observed_active")
    if any(c.get("active") != "inactive" or
           c.get("load") not in ("not-found", "masked", "loaded")
           for c in candidate):
        blockers.append("candidate_publisher_not_proven_inert")
    if shape.get("status") != "ok" or shape.get("legacy_contract") != "match":
        blockers.append("legacy_queue_schema_unverified")
    if q.get("status") != "ok" or q.get("policy_status") != "valid":
        blockers.append("legacy_queue_policy_unverified")
    if q.get("pause") not in ("not_paused", "paused"):
        blockers.append("legacy_pause_state_unverified")
    system_scout = by_name.get(("system", "bob-moltbook-scout.timer"), {})
    if system_scout.get("active") not in ("inactive",):
        blockers.append("legacy_system_scout_not_confirmed_inactive")
    if any(shape.get("additive_tables_present", ())):
        blockers.append("unexpected_r3_tables_need_manual_review")
    return {
        "format": "bob-r36-readonly-host-review-v1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "observation_only",
        "cutover_authorized": False,
        "new_publisher_installed_by_report": False,
        "legacy_publisher_is_only_authorized_writer": True,
        "baseline_observed": len(blockers) == 0,
        "review_blockers": blockers,
        "units": checked,
        "queue_contract": shape,
        "queue_state": {
            "status": q.get("status"),
            "pause": q.get("pause"),
            "auto_enabled": q.get("auto_enabled"),
            "policy_status": q.get("policy_status"),
            "policy_limits": q.get("policy_limits") if q.get("policy_status") == "valid" else {},
            "mode_counts": q.get("mode_counts") if q.get("status") == "ok" else {},
        },
        "production_cutover_requirements": [
            "real publisher admission of independently sealed Bob-authored text absent",
            "host-verified GET/friend proof and final pause check absent",
            "exact unit drop-ins, Windows/WSL reboot and publisher drain unverified",
            "owner has not approved a new v0.8 posting capability",
            "R2 naturally timed source-linked model decision still pending",
        ],
    }


def _allowed_field(key: str) -> frozenset[str]:
    # Values reflect the existing allowlisted unit probe, not systemctl raw text.
    from report_r3_cutover_inventory import (
        SAFE_LOAD, SAFE_ACTIVE, SAFE_SUB, SAFE_ENABLE, SAFE_RESULT,
    )
    return frozenset({
        "load": SAFE_LOAD, "active": SAFE_ACTIVE, "sub": SAFE_SUB,
        "enabled": SAFE_ENABLE, "result": SAFE_RESULT,
    }.get(key, ()))


def compact(report: dict) -> str:
    """Small, non-sensitive operator output; full sanitized JSON via --json."""
    unit = {(p["scope"], p["unit"]): p for p in report["units"]}
    def status(scope, name):
        return unit.get((scope, name), {}).get("active", "unknown")
    schema = report["queue_contract"]
    queue = report["queue_state"]
    blockers = report["review_blockers"]
    lines = [
        "R3.6 HOST READINESS (read-only, no cutover)",
        "legacy publisher timer: " + status("user", "bob-moltbook-publisher.timer"),
        "legacy publisher service: " + status("user", "bob-moltbook-publisher.service"),
        "shadow timer: " + status("user", "bob-v08-shadow.timer"),
        "startup reconcile timer: " + status("user", "bob-startup-reconcile.timer"),
        "candidate publisher timer: " + status("user", "bob-r3-candidate-publisher.timer"),
        "system legacy scout timer: " + status("system", "bob-moltbook-scout.timer"),
        "legacy queue schema: " + schema["legacy_contract"],
        "queue policy: " + str(queue["policy_status"]),
        "owner pause: " + str(queue["pause"]),
        "legacy auto comments: " + str(queue["auto_enabled"]),
        "historical attempted sends: " + str(schema["attempted_jobs"]),
        "delivery states requiring review: " + str(schema["uncertain_jobs"]),
        "baseline consistency: " + ("observed" if report["baseline_observed"] else "unverified"),
        "review blockers: " + (", ".join(blockers) if blockers else "none"),
        "new R3 publication authority: NONE",
        "cutover authorized: NO",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    import os
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("R3.6 REVIEW: refuse root")
        return 1
    if argv is None:
        argv = sys.argv[1:]
    if argv not in ([], ["--json"]):
        print("Usage: python3 scripts/report_r36_host_readiness.py [--json]")
        return 2
    facts = review()
    print(json.dumps(facts, sort_keys=True, indent=2) if argv == ["--json"]
          else compact(facts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
