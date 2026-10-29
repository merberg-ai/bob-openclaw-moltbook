#!/usr/bin/env python3
"""Regular-file two-file installer rehearsal. DISPOSABLE ONLY, NO LIVE MODE.

Models the real installed manager as a regular file, not a release symlink.
Persists a durable journal before the first file mutation. On interruption,
recovery restores manager and removes the newly added navigation module.
Never controls systemd, touches live HOME, or accesses production credentials.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

import build_v071_manager_candidate as builder

MARKER = "bob-v071-regular-file-disposable-v1"
PHASES = ("prepared", "navigation_installed", "manager_installed",
          "health_failed", "rollback_started", "complete", "incident")
CASES = ("healthy", "failed-health", "crash-navigation", "crash-manager")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fsync_dir(folder: Path):
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def safe(root: Path):
    if (root.is_symlink() or not root.is_dir()
            or not root.name.startswith("bob-v071-install-lab-")
            or stat.S_IMODE(root.stat().st_mode) & 0o077
            or (root / "LAB-ONLY").read_text() != MARKER):
        raise ValueError("not a disposable install lab")


def write_once(path: Path, content: bytes, mode: int):
    if path.exists() or path.is_symlink():
        raise ValueError("refusing pre-existing file")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    fsync_dir(path.parent)


def replace_file(path: Path, contents: bytes, expected_before: str | None, mode: int):
    if path.is_symlink():
        raise ValueError("symlink refused")
    if expected_before is None:
        if path.exists():
            raise ValueError("unexpected destination")
    elif not path.is_file() or digest(path.read_bytes()) != expected_before:
        raise ValueError("concurrent modification or unexpected file")
    staging = path.with_name("." + path.name + ".v071-pending")
    write_once(staging, contents, mode)
    os.replace(staging, path)
    fsync_dir(path.parent)


def journal(root: Path, phase: str):
    safe(root)
    if phase not in PHASES:
        raise ValueError("invalid phase")
    old = read_journal(root)
    if old and old["phase"] in ("complete", "incident"):
        raise ValueError("terminal transaction")
    target = root / "transaction.json"
    pending = root / ".transaction-pending"
    payload = json.dumps({"format": MARKER, "phase": phase}, sort_keys=True).encode()
    write_once(pending, payload, 0o600)
    os.replace(pending, target)
    fsync_dir(root)


def read_journal(root: Path):
    path = root / "transaction.json"
    if path.is_symlink():
        raise ValueError("symlink journal")
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 1024:
        raise ValueError("invalid journal")
    state = json.loads(path.read_text())
    if set(state) != {"format", "phase"} or state["format"] != MARKER or state["phase"] not in PHASES:
        raise ValueError("invalid transaction state")
    return state


def lock(root: Path):
    safe(root)
    fd = os.open(root / "transaction.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid != os.getuid():
        os.close(fd)
        raise ValueError("unsafe lock")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def stage() -> tuple[Path, tempfile.TemporaryDirectory]:
    temp = tempfile.TemporaryDirectory(prefix="bob-v071-install-lab-")
    root = Path(temp.name)
    try:
        write_once(root / "LAB-ONLY", MARKER.encode(), 0o600)
        (root / "bin").mkdir(mode=0o700)
        original = builder.SOURCE.read_bytes()
        if digest(original) != builder.PINNED_BASELINE_SHA256:
            raise ValueError("baseline checksum drift")
        write_once(root / "bin/bob-activity-manager", original, 0o700)
        candidate, navigation = builder.build()
        (root / "sealed").mkdir(mode=0o700)
        write_once(root / "sealed/baseline", original, 0o600)
        write_once(root / "sealed/candidate", candidate, 0o600)
        write_once(root / "sealed/navigation", navigation, 0o600)
        return root, temp
    except BaseException:
        temp.cleanup()
        raise


def sealed(root):
    safe(root)
    result = tuple((root / "sealed" / x).read_bytes() for x in ("baseline", "candidate", "navigation"))
    base, candidate, nav = result
    if (digest(base) != builder.PINNED_BASELINE_SHA256
            or candidate != builder.candidate_source(base, nav)):
        raise ValueError("sealed release drift")
    return result


def files(root):
    manager = root / "bin/bob-activity-manager"
    nav = root / "bin/navigation_shell.py"
    if manager.is_symlink() or not manager.is_file() or nav.is_symlink():
        raise ValueError("unsafe installed paths")
    return manager, nav


def install(root, interrupt=None):
    fd = lock(root)
    try:
        if read_journal(root) is not None:
            raise ValueError("existing transaction")
        baseline, candidate, navigation = sealed(root)
        manager, nav = files(root)
        if nav.exists() or digest(manager.read_bytes()) != digest(baseline):
            raise ValueError("initial installed state drift")
        journal(root, "prepared")
        replace_file(nav, navigation, None, 0o600)
        journal(root, "navigation_installed")
        if interrupt == "navigation":
            return "interrupted"
        replace_file(manager, candidate, digest(baseline), 0o700)
        journal(root, "manager_installed")
        if interrupt == "manager":
            return "interrupted"
        return "installed_pending_health"
    finally:
        os.close(fd)


def recover(root):
    fd = lock(root)
    try:
        state = read_journal(root)
        if state is None or state["phase"] in ("complete", "incident"):
            raise ValueError("no recoverable transaction")
        baseline, candidate, navigation = sealed(root)
        manager, nav = files(root)
        present = digest(manager.read_bytes())
        if present not in (digest(baseline), digest(candidate)):
            raise ValueError("installed manager modified unexpectedly")
        if nav.exists() and (not nav.is_file() or digest(nav.read_bytes()) != digest(navigation)):
            raise ValueError("installed navigation modified unexpectedly")
        journal(root, "rollback_started")
        if present == digest(candidate):
            replace_file(manager, baseline, digest(candidate), 0o700)
        if nav.exists():
            nav.unlink()
            fsync_dir(nav.parent)
        journal(root, "complete")
        return "baseline_restored"
    finally:
        os.close(fd)


def finish(root):
    fd = lock(root)
    try:
        state = read_journal(root)
        base, candidate, nav = sealed(root)
        manager, module = files(root)
        if (state is None or state["phase"] != "manager_installed"
                or digest(manager.read_bytes()) != digest(candidate)
                or not module.is_file() or digest(module.read_bytes()) != digest(nav)):
            raise ValueError("candidate not ready")
        journal(root, "complete")
    finally:
        os.close(fd)


def exercise(case):
    if case not in CASES:
        raise ValueError("unknown case")
    root, temp = stage()
    try:
        interruption = {"crash-navigation": "navigation", "crash-manager": "manager"}.get(case)
        install(root, interrupt=interruption)
        outcome = "candidate_healthy" if case == "healthy" else recover(root)
        if case == "healthy":
            finish(root)
        baseline, candidate, nav = sealed(root)
        manager, module = files(root)
        actual = digest(manager.read_bytes())
        expected = digest(candidate if case == "healthy" else baseline)
        if actual != expected or module.exists() != (case == "healthy"):
            raise AssertionError("wrong installed code state")
        return {"scenario": case, "outcome": outcome,
                "manager_sha256_expected": actual == expected,
                "navigation_present": module.exists(),
                "journal": read_journal(root)["phase"]}
    finally:
        temp.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=CASES, default="crash-manager")
    args = parser.parse_args()
    try:
        report = exercise(args.scenario)
    except (OSError, ValueError, RuntimeError, AssertionError, json.JSONDecodeError) as exc:
        print("v0.7.1 REGULAR-FILE INSTALL LAB: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 REGULAR-FILE INSTALL LAB: PASS")
    for key, value in report.items():
        print(key + ":", value)
    print("production_execution_available: NO; systemd_modified: NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
