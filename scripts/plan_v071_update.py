#!/usr/bin/env python3
"""v0.7.1 deployment planner: synthetic lifecycle ONLY, no production mode.

Never invokes systemctl, opens a network socket, or touches a real installation.
The candidate is checksum-verified against the repository's pinned baseline.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tempfile

import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import inspect_package, make_stage, switch, active, validate_release


class Phase(str, Enum):
    BASELINE = "baseline"
    STAGED = "staged"
    CANDIDATE_SELECTED = "candidate_selected"
    RESTART_REQUESTED = "restart_requested"
    HEALTH_CHECKED = "health_checked"
    ROLLBACK_SELECTED = "rollback_selected"
    RECOVERY_REQUESTED = "recovery_requested"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True)
class Result:
    success: bool
    restored: bool
    phases: tuple[str, ...]
    reason: str


def simulate(*, candidate_healthy: bool, recovery_healthy: bool = True,
             fail_at: str = "") -> Result:
    """Model state transitions with disposable releases and injected fake service results."""
    manager, nav = builder.build()
    manager, nav = inspect_package(builder.review_zip(manager, nav))
    baseline = builder.SOURCE.read_bytes()
    phases = [Phase.BASELINE.value]
    with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
        root = Path(tmp)
        make_stage(root, baseline, manager, nav)
        switch(root, "baseline")
        validate_release(root, "baseline")
        phases.append(Phase.STAGED.value)
        if fail_at == "pre_switch":
            return Result(False, True, tuple(phases), "pre_switch_refused")
        switch(root, "candidate")
        phases.append(Phase.CANDIDATE_SELECTED.value)
        # This models an adapter call; NO actual process or systemd invocation.
        phases.append(Phase.RESTART_REQUESTED.value)
        if fail_at == "restart":
            candidate_healthy = False
        if candidate_healthy:
            validate_release(root, "candidate")
            phases.extend((Phase.HEALTH_CHECKED.value, Phase.COMPLETE.value))
            return Result(True, False, tuple(phases), "candidate_healthy")
        # Failure after selection: restore code, then independently verify recovery.
        switch(root, "baseline")
        phases.extend((Phase.ROLLBACK_SELECTED.value, Phase.RECOVERY_REQUESTED.value))
        validate_release(root, "baseline")
        restored = active(root) == "baseline" and recovery_healthy
        phases.append(Phase.COMPLETE.value if restored else Phase.FAILED.value)
        return Result(False, restored, tuple(phases),
                      "rolled_back" if restored else "recovery_failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("success", "failed-health", "failed-recovery",
                                               "pre-switch", "restart-failure"),
                        default="failed-health")
    args = parser.parse_args()
    params = {
        "success": dict(candidate_healthy=True),
        "failed-health": dict(candidate_healthy=False),
        "failed-recovery": dict(candidate_healthy=False, recovery_healthy=False),
        "pre-switch": dict(candidate_healthy=True, fail_at="pre_switch"),
        "restart-failure": dict(candidate_healthy=True, fail_at="restart"),
    }[args.scenario]
    try:
        result = simulate(**params)
    except (ValueError, OSError, RuntimeError, SyntaxError, AssertionError) as exc:
        print("v0.7.1 SYNTHETIC UPDATER: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 SYNTHETIC UPDATER: COMPLETED")
    print("scenario:", args.scenario)
    print("outcome:", result.reason)
    print("baseline_restored:", result.restored)
    print("phases:", ",".join(result.phases))
    print("simulation_only: YES; deployable: NO")
    # A failure-injection scenario finishing as predicted is successful test execution.
    expected = {
        "success": (True, False, "candidate_healthy"),
        "failed-health": (False, True, "rolled_back"),
        "failed-recovery": (False, False, "recovery_failed"),
        "pre-switch": (False, True, "pre_switch_refused"),
        "restart-failure": (False, True, "rolled_back"),
    }[args.scenario]
    accepted = (result.success, result.restored, result.reason) == expected
    print("acceptance:", "PASS" if accepted else "REFUSED")
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
