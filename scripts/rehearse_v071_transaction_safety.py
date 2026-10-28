#!/usr/bin/env python3
"""Disposable v0.7.1 transaction safety lab. NEVER operates on installed Bob."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile

STATES = ("prepared", "candidate_selected", "restart_requested", "health_failed",
          "rollback_selected", "recovery_requested", "complete", "incident")
TERMINAL = ("complete", "incident")

def secure_root(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("invalid sandbox")
    if stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise ValueError("sandbox not private")
    if not root.name.startswith("bob-v071-journal-"):
        raise ValueError("not a synthetic sandbox")

@contextmanager
def exclusive(root: Path):
    secure_root(root)
    path = root / "transaction.lock"
    if path.is_symlink():
        raise ValueError("unsafe lock")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid != os.getuid():
            raise ValueError("unsafe lock file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another update holds lock") from exc
        yield
    finally:
        os.close(fd)

def read_journal(root: Path):
    path = root / "transaction.json"
    if path.is_symlink():
        raise ValueError("unsafe journal")
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 4096:
        raise ValueError("invalid journal")
    payload = json.loads(path.read_text())
    if (set(payload) != {"format", "phase", "scenario"}
            or payload["format"] != "v071-synthetic-v1"
            or payload["phase"] not in STATES
            or payload["scenario"] not in ("healthy", "failed-health", "failed-recovery")):
        raise ValueError("invalid journal state")
    return payload

def journal(root: Path, phase: str, scenario: str) -> None:
    secure_root(root)
    if phase not in STATES or scenario not in ("healthy", "failed-health", "failed-recovery"):
        raise ValueError("unknown transition")
    old = read_journal(root)
    if old is not None:
        if old["phase"] in TERMINAL or old["scenario"] != scenario:
            raise ValueError("old transaction requires review")
    tmp = root / ".journal-pending"
    if tmp.exists() or tmp.is_symlink():
        raise ValueError("stale temporary journal")
    data = json.dumps({"format": "v071-synthetic-v1", "phase": phase, "scenario": scenario}).encode()
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, root / "transaction.json")
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if tmp.exists():
            tmp.unlink()

class FakeService:
    """No subprocess, sockets, systemd, credentials, or actual service control."""
    def __init__(self, health: tuple[bool, ...]):
        self.outcomes = iter(health)
        self.restart_count = 0
        self.health_count = 0
    def restart(self):
        self.restart_count += 1
        if self.restart_count > 2:
            raise AssertionError("restart budget exceeded")
    def healthy(self):
        self.health_count += 1
        if self.health_count > 2:
            raise AssertionError("health budget exceeded")
        return next(self.outcomes, False)

def run(root: Path, scenario: str, service: FakeService) -> str:
    with exclusive(root):
        if read_journal(root) is not None:
            raise ValueError("unresolved or previous journal; fail closed")
        journal(root, "prepared", scenario)
        journal(root, "candidate_selected", scenario)
        service.restart()
        journal(root, "restart_requested", scenario)
        if service.healthy():
            journal(root, "complete", scenario)
            return "candidate_healthy"
        journal(root, "health_failed", scenario)
        journal(root, "rollback_selected", scenario)
        service.restart()
        journal(root, "recovery_requested", scenario)
        if service.healthy():
            journal(root, "complete", scenario)
            return "rolled_back"
        journal(root, "incident", scenario)
        return "recovery_failed"

def simulate(scenario: str) -> tuple[str, int, int]:
    if scenario not in ("healthy", "failed-health", "failed-recovery"):
        raise ValueError("invalid scenario")
    outcomes = {"healthy": (True,), "failed-health": (False, True),
                "failed-recovery": (False, False)}[scenario]
    with tempfile.TemporaryDirectory(prefix="bob-v071-journal-") as temp:
        service = FakeService(outcomes)
        result = run(Path(temp), scenario, service)
        return result, service.restart_count, service.health_count

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("healthy", "failed-health", "failed-recovery"),
                        default="failed-health")
    args = parser.parse_args()
    try:
        result, restarts, probes = simulate(args.scenario)
        expected = {"healthy": "candidate_healthy", "failed-health": "rolled_back",
                    "failed-recovery": "recovery_failed"}[args.scenario]
        if result != expected:
            raise ValueError("unexpected synthetic outcome")
    except (OSError, ValueError, AssertionError, json.JSONDecodeError) as exc:
        print("v0.7.1 TRANSACTION LAB: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 TRANSACTION LAB: PASS")
    print("scenario:", args.scenario)
    print("outcome:", result)
    print("synthetic_restarts:", restarts)
    print("synthetic_health_probes:", probes)
    print("live_service_modified: NO; deployable: NO")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
