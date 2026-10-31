#!/usr/bin/env python3
"""R3.5 offline rehearsal: synthetic migration, timer shape and rollback only.

Uses a private temporary fixture, no systemctl, no live queue, no credentials
and no Moltbook request. It deliberately DENIES new publisher activation.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from bob_v08.r35_migration_lab import MigrationFixture, reboot_reconcile
from bob_v08.r3_cutover_rehearsal import CutoverState, rehearse_cutover
from stage_service_graph import PREFIX, TIMERS, write_timer, write_service
from inventory_service_topology import safe_directives
from test_r35_migration_recovery import create_legacy_fixture


def inert_template_gate(root: Path) -> bool:
    """Check shapes of existing REPO staged templates, not installed units."""
    for role in TIMERS:
        timer = write_timer(role)
        target = PREFIX + role + ".service"
        if timer.count("Unit=" + target + "\n") != 1:
            return False
        meta = safe_directives(timer)
        if "Timer" not in meta["sections"] or not meta["timer_directives"]:
            return False
        if "OnUnitActiveSec" not in meta["timer_directives"] and role != "reconcile":
            return False
        service = write_service(root, role)
        parsed = safe_directives(service)
        if parsed.get("service_type") != "oneshot":
            return False
        if not service.startswith("# INERT STAGING ONLY"):
            return False
    return True


def report() -> dict:
    with tempfile.TemporaryDirectory(prefix="bob-r35-") as dirname:
        root = Path(dirname)
        path = root / "r35-inert-fixtures" / "r35-legacy-queue-lab.sqlite3"
        create_legacy_fixture(path)
        fixture = MigrationFixture(path)
        before = fixture.history_summary()
        crashed = False
        try:
            fixture.migrate(inject_crash=True)
        except RuntimeError as err:
            crashed = str(err) == "synthetic_power_loss_after_ddl"
        if not crashed or fixture.history_summary() != before:
            raise AssertionError("inert DDL crash rollback failed")
        result = fixture.migrate()
        repeated = fixture.migrate()
        if result != repeated or fixture.history_summary() != before:
            raise AssertionError("migration changed legacy history")
        if not inert_template_gate(root):
            raise AssertionError("inert service template mismatch")
        baseline = CutoverState(attempted=("legacy_attempt",),
                                uncertain=("legacy_uncertain",))
        staged = rehearse_cutover(baseline, "stage")
        quiesced = rehearse_cutover(staged.state, "quiesce",
                                   legacy_drained=True,
                                   backup_verified=True,
                                   rollback_rehearsed=True)
        denied = rehearse_cutover(quiesced.state, "activate",
                                  owner_explicitly_authorized=False,
                                  backup_verified=True,rollback_rehearsed=True,
                                  source_adapter_verified=True)
        reboot = reboot_reconcile(quiesced.state,
                                  legacy_timer=False,candidate_timer=False,
                                  legacy_worker=False,candidate_worker=False,
                                  startup_reconcile_verified=True)
        rollback = rehearse_cutover(quiesced.state, "rollback")
        if not (staged.accepted and quiesced.accepted
                and not denied.accepted and not reboot.safe_to_resume
                and rollback.accepted and rollback.state == baseline):
            raise AssertionError("exclusive ownership/restart invariant failed")
        return {
            "format": "bob-r35-inert-deployment-v1",
            "legacy_schema_additive": result.migrated,
            "legacy_history_preserved": result.preserved_legacy_rows,
            "migration_idempotent": repeated == result,
            "crash_before_commit_rolled_back": crashed,
            "inert_service_templates_checked": len(TIMERS),
            "unapproved_cutover_denied": not denied.accepted,
            "unverified_reboot_kept_paused": not reboot.safe_to_resume,
            "rollback_preserves_unknowns": rollback.state.uncertain == baseline.uncertain,
            "cutover_authorized": False,
            "live_unit_changes": 0,
            "external_requests": 0,
        }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
