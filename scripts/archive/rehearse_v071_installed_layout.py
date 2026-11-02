#!/usr/bin/env python3
"""v0.7.1 synthetic installed-layout transaction; NEVER a live installer."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import tempfile
import stat
import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import inspect_package

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def put(path: Path, data: bytes, mode: int) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("existing staging member")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(fd, "wb") as out:
        out.write(data)

def verify(root: Path, candidate: bytes, nav: bytes) -> None:
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise ValueError("unsafe stage root")
    installed = root / "installed/bob-activity-manager"
    if installed.is_symlink() or not installed.is_file() or digest(installed.read_bytes()) != builder.PINNED_BASELINE_SHA256:
        raise ValueError("installed manager drift")
    for name, payload in (("bob-activity-manager", candidate), ("navigation_shell.py", nav)):
        file = root / "releases/v071" / name
        if file.is_symlink() or not file.is_file() or file.read_bytes() != payload:
            raise ValueError("candidate release incomplete")

def rehearse(fail_health: bool = True) -> dict:
    candidate, nav = builder.build()
    candidate, nav = inspect_package(builder.review_zip(candidate, nav))
    baseline = builder.SOURCE.read_bytes()
    with tempfile.TemporaryDirectory(prefix="bob-v071-installed-") as temp:
        root = Path(temp)
        for folder in ("installed", "releases", "releases/v071"):
            (root / folder).mkdir(mode=0o700)
        installed = root / "installed/bob-activity-manager"
        put(installed, baseline, 0o700)
        put(root / "releases/v071/bob-activity-manager", candidate, 0o700)
        put(root / "releases/v071/navigation_shell.py", nav, 0o600)
        verify(root, candidate, nav)
        # A future production updater must select a versioned executable via
        # a reviewed service launch contract; never replace a live file here.
        pointer = root / "current"
        pending = root / ".pending"
        pending.symlink_to("installed")
        os.replace(pending, pointer)
        old = os.readlink(pointer)
        pending.symlink_to("releases/v071")
        os.replace(pending, pointer)
        if os.readlink(pointer) != "releases/v071":
            raise AssertionError("candidate switch failed")
        if fail_health:
            pending.symlink_to(old)
            os.replace(pending, pointer)
            if os.readlink(pointer) != "installed":
                raise AssertionError("rollback failed")
        else:
            if os.readlink(pointer) != "releases/v071":
                raise AssertionError("healthy candidate not selected")
        if digest(installed.read_bytes()) != builder.PINNED_BASELINE_SHA256:
            raise AssertionError("original executable changed")
    return {"staged_two_files": True, "original_manager_preserved": True,
            "synthetic_health_failure_rollback": fail_health,
            "no_production_change": True}

def main() -> int:
    try:
        results = rehearse()
    except (OSError, ValueError, SyntaxError, AssertionError) as exc:
        print("v0.7.1 INSTALLED LAYOUT REHEARSAL: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 INSTALLED LAYOUT REHEARSAL: PASS")
    for key, value in results.items():
        print(key + ":", value)
    print("Synthetic private temp only; no service or database accessed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
