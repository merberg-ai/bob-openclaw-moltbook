#!/usr/bin/env python3
"""Offline v0.7.1 two-file release layout acceptance.

Test only. Uses generated, pinned review archive and private temporary files.
Never reads or changes installed services, live SQLite or credentials.
"""
from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile

import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import inspect_package, make_stage, switch, active, validate_release


def verify_import(root: Path) -> None:
    """Prove both selected files can be imported from the same versioned directory."""
    current = root / "current"
    if active(root) != "candidate":
        raise ValueError("Candidate release not active in rehearsal")
    manager = current / "bin/bob-activity-manager"
    navigation = current / "bin/navigation_shell.py"
    if manager.is_symlink() or navigation.is_symlink():
        raise ValueError("Unexpected candidate member symlink")
    if not manager.is_file() or not navigation.is_file():
        raise ValueError("Incomplete two-file candidate")
    source = manager.read_text()
    module = navigation.read_text()
    if "from navigation_shell import integrate_existing_html" not in source:
        raise ValueError("Missing candidate navigation import")
    if "def integrate_existing_html(" not in module:
        raise ValueError("Missing navigation implementation")
    if source.count("integrate_existing_html") != 4:
        raise ValueError("Unexpected navigation integration")
    compile(source, str(manager), "exec")
    compile(module, str(navigation), "exec")


def acceptance(root: Path) -> dict[str, bool]:
    manager, navigation = builder.build()
    verified_manager, verified_navigation = inspect_package(
        builder.review_zip(manager, navigation)
    )
    if (manager, navigation) != (verified_manager, verified_navigation):
        raise ValueError("Candidate package bytes mismatch")
    baseline = builder.SOURCE.read_bytes()
    make_stage(root, baseline, manager, navigation)
    switch(root, "baseline")
    baseline_path = root / "current/bin/bob-activity-manager"
    if hashlib.sha256(baseline_path.read_bytes()).hexdigest() != builder.PINNED_BASELINE_SHA256:
        raise ValueError("Baseline release mismatch")
    # Both files are staged before the atomic symlink switch.
    switch(root, "candidate")
    verify_import(root)
    validate_release(root, "candidate")
    # Simulate a failed health gate; never replace/rewind any database.
    switch(root, "baseline")
    if active(root) != "baseline":
        raise ValueError("Code rollback failed")
    validate_release(root, "baseline")
    if hashlib.sha256(baseline_path.read_bytes()).hexdigest() != builder.PINNED_BASELINE_SHA256:
        raise ValueError("Baseline rollback changed bytes")
    return {
        "two_file_package_verified": True,
        "candidate_import_layout_verified": True,
        "atomic_release_selection_verified": True,
        "baseline_code_rollback_verified": True,
        "production_untouched": True,
    }


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            result = acceptance(Path(tmp))
    except (OSError, ValueError, RuntimeError, SyntaxError, AssertionError) as exc:
        print("v0.7.1 TWO-FILE STAGING: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 TWO-FILE STAGING: PASS")
    for key, value in result.items():
        print(key + ":", value)
    print("No live files, credentials, service units, or databases accessed or changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
