#!/usr/bin/env python3
"""One read-only R4 PROMOTED source + live OMEN host GO/NO-GO review.

No updater, schema migration, service mutation, R4 proposal run, Moltbook
request, release promotion, or permission change. A passing report means
"ready for a SEPARATELY authorized owner installation", NOT authorization
to install or enable R4 social sends.

Run after a source-only merge to next:
    python3 scripts/report_r4_go_nogo.py --check
"""
from __future__ import annotations

import json
import os
import sys

import report_r4_candidate
import report_r4_preinstall

EXPECTED_SOURCE = "v0.8.0-autonomy1"
EXPECTED_INSTALLED = "v0.8.0-r3canary1"


def inspect(*, source_probe=None, host_probe=None) -> dict:
    """Always report individual sanitized gate results, fail closed.

    Dependency injection is exclusively for synthetic tests. Real CLI uses
    fixed reviewed scripts which do not create files or contact Moltbook.
    """
    get_source = report_r4_candidate.inspect if source_probe is None else source_probe
    get_host = report_r4_preinstall.inspect if host_probe is None else host_probe
    source_ok = False
    host_ok = False
    blockers = []
    host_checks = {name: False for name in report_r4_preinstall.REQUIRED}
    files = 0
    try:
        candidate = get_source()
        source_ok = (candidate.get("candidate") == EXPECTED_SOURCE
                     and candidate.get("release_manifest") == EXPECTED_SOURCE
                     and candidate.get("promotion_state") == "promoted_exact_candidate"
                     and candidate.get("previous_installed_release") == EXPECTED_INSTALLED
                     and candidate.get("files") == 23
                     and candidate.get("candidate_source_build") == "PASS"
                     and candidate.get("exact_https_generated_manager") is True
                     and candidate.get("all_new_auto_modes_compiled_off") is True
                     and candidate.get("legacy_r3_publisher_not_replaced") is True
                     and candidate.get("install_authorized") is False
                     and candidate.get("real_social_action_authorized") is False)
        if source_ok:
            files = 23
    except (OSError, RuntimeError, ValueError, TypeError, KeyError,
            ImportError, AttributeError, UnicodeError, SyntaxError):
        source_ok = False
    if not source_ok:
        blockers.append("candidate_source_review")
    try:
        host = get_host()
        checks = host.get("checks")
        if (type(checks) is dict and set(checks) == set(host_checks)
                and all(type(v) is bool for v in checks.values())):
            host_checks = dict(checks)
        host_ok = (host.get("currently_installed_expected") == EXPECTED_INSTALLED
                   and host.get("target_candidate") == EXPECTED_SOURCE
                   and host.get("ready_for_separate_owner_install_prompt") is True
                   and host.get("installation_authorized") is False
                   and host.get("real_r4_send_authorized") is False
                   and all(host_checks.values()))
    except (OSError, RuntimeError, ValueError, TypeError, KeyError,
            ImportError, AttributeError, UnicodeError, SyntaxError):
        host_ok = False
    if not host_ok:
        blockers.extend("host_" + name for name, ok in host_checks.items() if not ok)
        if all(host_checks.values()):
            blockers.append("host_attestation_incomplete")
    return {
        "format": "r4-single-readonly-go-nogo-v1",
        "source_candidate": EXPECTED_SOURCE,
        "currently_installed_expected": EXPECTED_INSTALLED,
        "candidate_source_verified": source_ok,
        "promoted_manifest_verified": source_ok,
        "candidate_files_checked": files,
        "live_host_readiness_verified": host_ok,
        "host_checks": host_checks,
        "blockers": sorted(set(blockers)),
        "ready_for_separate_release_review": source_ok and host_ok,
        "ready_for_separate_owner_install_prompt": source_ok and host_ok,
        "r4_installed_by_report": False,
        "install_authorized_by_report": False,
        "real_r4_social_sends_authorized": False,
        "host_files_changed_by_report": False,
        "systemd_changed_by_report": False,
        "database_changed_by_report": False,
        "moltbook_api_requests_by_report": 0,
    }


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--check"]:
        print("Usage: python3 scripts/report_r4_go_nogo.py --check")
        return 2
    if os.geteuid() == 0:
        print("R4 GO-NO-GO: REFUSED (non-root owner required)")
        return 1
    report = inspect()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["ready_for_separate_release_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
