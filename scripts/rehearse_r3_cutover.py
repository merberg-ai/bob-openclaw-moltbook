#!/usr/bin/env python3
"""Print R3.4 inert cutover rehearsal verdict, no system services or live DB.

This intentionally demonstrates the SAFE refusal when owner approval is absent.
It is source-only; does not inspect the OMEN, call systemctl or install units.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bob_v08.r3_cutover_rehearsal import CutoverState, rehearse_cutover


def report() -> dict:
    baseline = CutoverState(
        attempted=("historical_attempt_preserved",),
        uncertain=("ambiguous_delivery_preserved",))
    staged = rehearse_cutover(baseline, "stage")
    quiesced = rehearse_cutover(
        staged.state, "quiesce", legacy_drained=True,
        backup_verified=True, rollback_rehearsed=True)
    # No owner grant is supplied. This MUST be denied.
    unauthorized = rehearse_cutover(
        quiesced.state, "activate", source_adapter_verified=True,
        backup_verified=True, rollback_rehearsed=True)
    rollback = rehearse_cutover(quiesced.state, "rollback")
    if not (staged.accepted and quiesced.accepted and not unauthorized.accepted
            and rollback.accepted and rollback.state == baseline):
        raise AssertionError("synthetic cutover invariant failed")
    return {
        "format": "bob-r34-inert-cutover-rehearsal-v1",
        "authority": "synthetic_only_no_host_action",
        "cutover_authorized": False,
        "network_attempts": 0,
        "systemd_changes": 0,
        "owner_permission_absent": unauthorized.reason,
        "staging_reached": quiesced.state.phase,
        "rolled_back_to": rollback.state.phase,
        "attempt_history_preserved": rollback.state.attempted == baseline.attempted,
        "uncertain_history_preserved": rollback.state.uncertain == baseline.uncertain,
        "shadow_timer_unchanged": rollback.state.shadow_timer == baseline.shadow_timer,
    }


def main() -> int:
    print(json.dumps(report(),sort_keys=True,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
