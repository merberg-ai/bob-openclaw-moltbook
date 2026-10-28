#!/usr/bin/env python3
"""Inert child-process lifecycle rehearsal, NOT a systemd service start.

Runs only the six-role mock fixture in a private TemporaryDirectory.
Starts/reaps two wait-only mock processes; simulates a crash, candidate release
restart, and code rollback. Network/publishing remain disabled by exact mock
config. No systemctl, daemon-reload, external API, real unit, or live SQLite.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time

from stage_service_graph import PREFIX, create, point_to, verify
from stage_mock_actor import ROLES

LIVE_ROLES = ("gateway", "manager")
EVENT_TIMEOUT = 5.0
REAP_TIMEOUT = 3.0


def event_rows(root: Path) -> list[tuple[str, str]]:
    with closing(sqlite3.connect(root / "private" / "synthetic.sqlite3", timeout=2)) as db:
        return db.execute(
            "SELECT role, release_tag FROM simulated_events ORDER BY id"
        ).fetchall()


def await_rows(root: Path, count: int, *, timeout: float = EVENT_TIMEOUT) -> list:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rows = event_rows(root)
        if len(rows) >= count:
            return rows
        time.sleep(0.03)
    raise RuntimeError("Mock role did not acknowledge startup")


def start_mock(root: Path, role: str) -> subprocess.Popen:
    if role not in LIVE_ROLES or role not in ROLES:
        raise ValueError("Only inert Gateway/Manager role starts permitted")
    verify(root)
    actor = root / "current" / "bin" / "stage_mock_actor.py"
    if actor.is_symlink() or not actor.is_file():
        raise ValueError("Mock executable is not a regular file")
    meta = __import__("json").loads((root / "STAGING-GRAPH.json").read_text())
    if hashlib.sha256(actor.read_bytes()).hexdigest() != meta["fixture_sha256"]:
        raise ValueError("Mock fixture has changed")
    return subprocess.Popen(
        [sys.executable, str(actor), "--stage-root", str(root),
         "--role", role, "--serve"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=root, start_new_session=True,
        env={"HOME": str(root / "private"), "PATH": "/usr/bin:/bin",
             "PYTHONDONTWRITEBYTECODE": "1"},
    )


def reap(proc: subprocess.Popen, *, crash: bool = False) -> None:
    if proc.poll() is None:
        try:
            # Child is in its own process session: no live Bob PID can be
            # addressed. Never use pkill, systemctl, or a broad process match.
            os.killpg(proc.pid, signal.SIGKILL if crash else signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=REAP_TIMEOUT)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=REAP_TIMEOUT)


def exercise(root: Path) -> dict:
    verify(root)
    children: list[subprocess.Popen] = []
    crashed = False
    try:
        gw = start_mock(root, "gateway")
        children.append(gw)
        manager = start_mock(root, "manager")
        children.append(manager)
        rows = await_rows(root, 2)
        if set(rows) != {("gateway", "baseline"), ("manager", "baseline")}:
            raise AssertionError("Baseline mock startup mismatch")
        if gw.poll() is not None or manager.poll() is not None:
            raise AssertionError("Mock role exited prematurely")
        reap(gw, crash=True)
        crashed = gw.returncode is not None and gw.returncode != 0
        if not crashed:
            raise AssertionError("Mock gateway crash was not observed")
        restarted = start_mock(root, "gateway")
        children.append(restarted)
        rows = await_rows(root, 3)
        if rows.count(("gateway", "baseline")) != 2:
            raise AssertionError("Simulated gateway restart not observed")
        if restarted.poll() is not None or manager.poll() is not None:
            raise AssertionError("Mock restart not sustained")
        reap(restarted)
        reap(manager)
        point_to(root, "candidate")
        gw2 = start_mock(root, "gateway")
        children.append(gw2)
        manager2 = start_mock(root, "manager")
        children.append(manager2)
        rows = await_rows(root, 5)
        if set(rows[3:]) != {("gateway", "candidate"), ("manager", "candidate")}:
            raise AssertionError("Candidate mock startup mismatch")
        if gw2.poll() is not None or manager2.poll() is not None:
            raise AssertionError("Candidate mock role exited")
        reap(gw2)
        reap(manager2)
        point_to(root, "baseline")
        gw3 = start_mock(root, "gateway")
        children.append(gw3)
        manager3 = start_mock(root, "manager")
        children.append(manager3)
        rows = await_rows(root, 7)
        if set(rows[5:]) != {("gateway", "baseline"), ("manager", "baseline")}:
            raise AssertionError("Rollback mock startup mismatch")
        reap(gw3)
        reap(manager3)
        if any(p.poll() is None for p in children):
            raise AssertionError("Mock child remained running")
        with closing(sqlite3.connect(root / "private" / "synthetic.sqlite3")) as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise AssertionError("Mock SQLite integrity check failed")
        verify(root)
        return {
            "mock_long_running_starts": len(children),
            "crash_observed": crashed,
            "mock_restart_verified": True,
            "candidate_switch_verified": True,
            "rollback_restart_verified": True,
            "post_swap_state_preserved": len(rows) == 7,
            "children_reaped": True,
            "live_install_modified": False,
        }
    finally:
        # Always reap ONLY the PIDs spawned by this simulation, even if an
        # assertion or SQLite error interrupted the rehearsal.
        for child in reversed(children):
            reap(child)


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("Run mock rehearsal as unprivileged OpenClawLab user")
    try:
        with tempfile.TemporaryDirectory(prefix=PREFIX) as temp:
            root = Path(temp)
            create(root)
            result = exercise(root)
    except (OSError, ValueError, AssertionError, RuntimeError, sqlite3.Error,
            subprocess.SubprocessError) as exc:
        print("INERT PROCESS LIFECYCLE: REFUSED", type(exc).__name__,
              "(production untouched)", file=sys.stderr)
        return 1
    print("INERT PROCESS LIFECYCLE: PASS")
    for key, value in result.items():
        print(" ", key + ":", value)
    print("All spawned mock processes reaped; synthetic sandbox removed.")
    print("No actual systemd unit, live worker, API, or Windows startup touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
