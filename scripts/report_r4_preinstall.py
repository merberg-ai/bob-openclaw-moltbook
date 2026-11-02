#!/usr/bin/env python3
"""R4 preinstallation release/host readiness, READ ONLY, never an installer.

This is the exact R3 canary -> autonomy1 source/host gate. Older R3 proposal
handoff gates deliberately do not recognize r3canary1 and MUST NOT be used
for the R4 upgrade. No API, private credentials in output, schema writes,
service mutations or publisher activation. Never treats a report as consent.
"""
from __future__ import annotations

import json
import os
import sys

import bob_release_updater as updater

RELEASE = "v0.8.0-r3canary1"
REQUIRED = (
    "signed_r3_canary",
    "owner_identity",
    "existing_worker_topology",
    "effective_original_publisher_units",
    "publisher_inactive",
    "authenticated_https",
    "no_incomplete_update",
)


def signed_r3_canary() -> bool:
    from report_r3_canary_installed import _signed_scope
    return _signed_scope()


def owner_identity() -> bool:
    from r3_service_handoff import _owner
    return _owner()


def existing_worker_topology() -> bool:
    from report_r3_diagnostic_installed import _units_ok
    # Existing active Scout, R3 proposal and original publisher timer,
    # disabled R2 shadow, no competing R3 credentialed publisher.
    return _units_ok()


def effective_original_publisher_units() -> bool:
    from report_r38_effective_units import report
    info = report()
    return (info["effective_service"] == "reviewed_shape"
            and info["effective_timer"] == "reviewed_shape"
            and info["review_blockers"] == []
            and info["cutover_authorized"] is False)


def publisher_inactive() -> bool:
    return updater.r4_publisher_inactive()


def authenticated_https() -> bool:
    return (updater.manager_transport(RELEASE) == "https"
            and updater.healthy(updater.authorization(), release=RELEASE))


def no_incomplete_update() -> bool:
    journal = updater.read_journal()
    # Last successful R3 signed update has a completed journal; absence is
    # allowed for older clean compatible baselines. A pending or incident
    # transaction must be inspected/recovered separately, never auto-fixed.
    return journal is None or journal["phase"] in ("complete", "rolled_back")


def inspect(*, checks=None) -> dict:
    """Safe bounded report: only boolean review results and static labels.

    Callback injection is for tests only; production CLI and updater call
    the default real fixed-host checks. Any exception is a fail-closed check.
    """
    probes = (checks if checks is not None else {
        "signed_r3_canary": signed_r3_canary,
        "owner_identity": owner_identity,
        "existing_worker_topology": existing_worker_topology,
        "effective_original_publisher_units":
            effective_original_publisher_units,
        "publisher_inactive": publisher_inactive,
        "authenticated_https": authenticated_https,
        "no_incomplete_update": no_incomplete_update,
    })
    if set(probes) != set(REQUIRED):
        raise ValueError("r4_unreviewed_preinstall_probes")
    observations = {}
    for name in REQUIRED:
        try:
            observations[name] = probes[name]() is True
        except (OSError, ValueError, RuntimeError, TypeError, KeyError,
                ImportError, AttributeError, UnicodeError):
            observations[name] = False
    return {
        "format": "r4-preinstall-host-review-v1",
        "currently_installed_expected": RELEASE,
        "target_candidate": "v0.8.0-autonomy1",
        "checks": observations,
        "blockers": sorted(k for k, ok in observations.items() if not ok),
        "ready_for_separate_owner_install_prompt": all(observations.values()),
        "installation_authorized": False,
        "real_r4_send_authorized": False,
        "database_changed": False,
        "systemd_changed": False,
        "moltbook_requests": 0,
    }


def main(args=None) -> int:
    args = sys.argv[1:] if args is None else args
    if args != ["--check"]:
        print("Usage: python3 scripts/report_r4_preinstall.py --check")
        return 2
    if os.geteuid() == 0:
        print("R4 PREINSTALL REFUSED: non-root owner required")
        return 1
    report = inspect()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["ready_for_separate_owner_install_prompt"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
