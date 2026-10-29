#!/usr/bin/env python3
"""Production deployment controller PHASE 1: fail-closed READ-ONLY release plan.

No install, stage writes, systemctl restart, health mutation or deploy flag.
The plan is intentionally an observation, not authorization for live changes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import inspect_package
from preflight_v071_effective_service import classify, query
from preflight_v071_live import check_backup

APPROVED_MANAGER = Path.home() / ".local/bin/bob-activity-manager"
APPROVED_BACKUP_DIR = Path.home() / ".local/state/bob-baseline/backups"
APPROVED_UNIT = "bob-activity-manager.service"
FIELDS = ("installed_manager_pinned", "installed_manager_regular_private",
          "effective_user_service_contract", "private_recent_sqlite_backup",
          "candidate_package_valid", "candidate_changes_from_baseline",
          "navigation_module_present")


def validate_path(path: Path, expected: Path, *, mode_required: int = 0) -> bool:
    if path != expected or path.is_symlink():
        return False
    try:
        st = path.stat()
    except OSError:
        return False
    return stat.S_ISREG(st.st_mode) and not (stat.S_IMODE(st.st_mode) & mode_required)


def plan(backup: Path) -> dict:
    # Do not follow arbitrary operator-supplied paths or output sensitive values.
    if (not backup.is_absolute() or backup.is_symlink()
            or backup.parent != APPROVED_BACKUP_DIR
            or not backup.name.startswith("bob-activity-")
            or backup.suffix != ".sqlite3"):
        raise ValueError("backup path outside approved private directory")
    raw = query()
    contract = classify(raw, manager=APPROVED_MANAGER)
    manager_safe = validate_path(APPROVED_MANAGER, APPROVED_MANAGER, mode_required=0o022)
    candidate, nav = builder.build()
    zipped_manager, zipped_nav = inspect_package(builder.review_zip(candidate, nav))
    checks = {
        "installed_manager_pinned": contract["pinned_installed_executable"],
        "installed_manager_regular_private": manager_safe,
        "effective_user_service_contract": all(
            value for key, value in contract.items() if key != "pinned_installed_executable"),
        "private_recent_sqlite_backup": check_backup(backup),
        "candidate_package_valid": (candidate, nav) == (zipped_manager, zipped_nav),
        "candidate_changes_from_baseline": builder.sha256(candidate) != builder.PINNED_BASELINE_SHA256,
        "navigation_module_present": bool(nav) and b"integrate_existing_html" in nav,
    }
    if tuple(checks) != FIELDS:
        raise AssertionError("plan schema mismatch")
    return {"checks": checks, "ready_for_separate_deployment_review": all(checks.values()),
            "live_install_modified": False, "production_execution_available": False,
            "candidate_manager_sha256": builder.sha256(candidate),
            "candidate_navigation_sha256": builder.sha256(nav)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True, type=Path)
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("root is not an approved operator")
    try:
        result = plan(args.backup)
    except (OSError, ValueError, AssertionError, RuntimeError) as exc:
        print("v0.7.1 PRODUCTION CONTROLLER PLAN: REFUSED", type(exc).__name__)
        return 1
    for key, value in result["checks"].items():
        print(key + ":", "PASS" if value else "REFUSED")
    print("candidate_manager_sha256:", result["candidate_manager_sha256"])
    print("candidate_navigation_sha256:", result["candidate_navigation_sha256"])
    print("v0.7.1 PRODUCTION CONTROLLER PLAN:",
          "PASS" if result["ready_for_separate_deployment_review"] else "REFUSED")
    print("production_execution_available: NO; live_install_modified: NO")
    return 0 if result["ready_for_separate_deployment_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
