#!/usr/bin/env python3
"""R3.13a fixed-host audit and opt-in PRIVATE-COPY migration rehearsal.

Run from a clean development checkout in OpenClawLab, as the normal WSL user.
No arbitrary database paths, systemd mutations, credentials or network APIs.
Even a passing report never authorizes installation or Moltbook publication.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bob_v08.r313a_private_migration import inspect_boundary, rehearse
from report_r3_cutover_inventory import QUEUE, PAUSED
from report_r38_effective_units import report as unit_report


def collect(*, private_copy: bool = False) -> dict:
    fixed = {"home": Path.home(), "queue": QUEUE,
             "paused": PAUSED, "uid": os.geteuid()}
    boundary = (rehearse(**fixed) if private_copy else
                {"host": inspect_boundary(**fixed),
                 "rehearsal": "not_requested",
                 "cutover_authorized": False})
    return {
        "format": "bob-r313a-host-preflight-v1",
        "host": boundary["host"],
        "effective_units": unit_report(),
        "rehearsal": boundary["rehearsal"],
        "publisher_code_integrity": "not_verified",
        "new_r3_owner_permission": "not_granted",
        "live_schema_migration": "not_performed",
        "dispatch_authorized": False,
        "cutover_authorized": False,
        "external_requests": 0,
    }


def compact(data: dict) -> str:
    h = data["host"]
    u = data["effective_units"]
    migration = data["rehearsal"]
    lines = [
        "R3.13a TRUSTED HOST / PRIVATE MIGRATION (no cutover)",
        "source root: " + h["source_root"],
        "queue file: " + h["queue_file"],
        "pause: " + h["pause"],
        "legacy schema: " + h["legacy_schema"],
        "additive schema: " + h["additive_schema"],
        "R3 owner settings: " + h["r3_settings"],
        "private copy eligible: " + ("yes" if h["private_copy_eligible"] else "no"),
        "effective publisher service: " + u["effective_service"],
        "effective publisher timer: " + u["effective_timer"],
        "boundary blockers: " + (", ".join(h["review_blockers"]) or "none"),
        "unit blockers: " + (", ".join(u["review_blockers"]) or "none"),
    ]
    if isinstance(migration, dict):
        lines += [
            "private copy migration: " + ("PASS" if migration.get(
                "private_copy_migrated") else "FAILED"),
            "legacy history preserved: " + str(migration.get(
                "full_legacy_history_preserved", False)),
            "crash rollback: " + str(migration.get("crash_rollback_pass", False)),
            "idempotent: " + str(migration.get("idempotent", False)),
            "historical send attempts: " + str(migration.get("historical_attempts")),
            "historical uncertain states: " + str(migration.get("historical_uncertain")),
            "private copy: deleted",
        ]
    else:
        lines.append("private copy rehearsal: " + migration)
    lines += ["live database changed: NO", "publisher changes: NONE",
              "new R3 send permissions: NONE", "R3 cutover authorized: NO"]
    return "\n".join(lines)


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv not in ([], ["--json"], ["--private-copy"], ["--private-copy", "--json"]):
        print("Usage: python3 scripts/report_r313a_host.py "
              "[--private-copy] [--json]")
        return 2
    if os.geteuid() == 0:
        print("R3.13a HOST REVIEW: refuse root")
        return 1
    result = collect(private_copy="--private-copy" in argv)
    print(json.dumps(result, sort_keys=True, indent=2) if "--json" in argv
          else compact(result))
    outcome = result["rehearsal"]
    if "--private-copy" in argv and not (
            isinstance(outcome, dict) and outcome.get("private_copy_migrated")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
