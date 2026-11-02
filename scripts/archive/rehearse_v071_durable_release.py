#!/usr/bin/env python3
"""Durable release transaction on a DISPOSABLE filesystem. No production mode.

Crash injection leaves a journal on disk; a later invocation recovers the
baseline without reverting SQLite writes. This controller never calls systemd.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import make_stage, switch, active, validate_release

FORMAT = "v071-durable-disposable-v1"
PHASES = ("prepared", "candidate_selected", "restart_requested",
          "health_failed", "rollback_selected", "recovery_requested",
          "complete", "incident")


def check_root(root: Path) -> None:
    if (root.is_symlink() or not root.is_dir()
            or not root.name.startswith("bob-v071-ui-")
            or stat.S_IMODE(root.stat().st_mode) & 0o077):
        raise ValueError("unsafe disposable root")
    if (root / "STAGING-ONLY").read_text() != "bob-v071-ui-staging-v1":
        raise ValueError("missing synthetic marker")


def sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def record(root: Path, phase: str) -> None:
    check_root(root)
    if phase not in PHASES:
        raise ValueError("invalid phase")
    previous = read_record(root)
    if previous and previous["phase"] in ("complete", "incident"):
        raise ValueError("transaction closed")
    staging = root / ".transaction-pending"
    if staging.exists() or staging.is_symlink():
        raise ValueError("stale transaction pending")
    payload = json.dumps({"format": FORMAT, "phase": phase,
                          "baseline_sha256": builder.PINNED_BASELINE_SHA256},
                         sort_keys=True).encode()
    fd = os.open(staging, os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(staging, root / "transaction.json")
        sync_dir(root)
    finally:
        staging.unlink(missing_ok=True)


def read_record(root: Path):
    file = root / "transaction.json"
    if file.is_symlink():
        raise ValueError("journal symlink")
    if not file.exists():
        return None
    if not file.is_file() or file.stat().st_size > 1024:
        raise ValueError("invalid journal file")
    obj = json.loads(file.read_text())
    if (set(obj) != {"format", "phase", "baseline_sha256"}
            or obj["format"] != FORMAT or obj["phase"] not in PHASES
            or obj["baseline_sha256"] != builder.PINNED_BASELINE_SHA256):
        raise ValueError("journal mismatch")
    return obj


def locked(root: Path):
    check_root(root)
    fd = os.open(root / "transaction.lock",
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid != os.getuid():
        os.close(fd)
        raise ValueError("invalid lock")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def preserve_write(root: Path, value: str):
    db_file = root / "state/synthetic.sqlite3"
    if db_file.is_symlink() or not db_file.is_file():
        raise ValueError("unsafe SQLite fixture")
    with closing(sqlite3.connect(db_file)) as db:
        db.execute("INSERT INTO events (phase) VALUES (?)", (value,))
        db.commit()


def data_preserved(root: Path, expected):
    with closing(sqlite3.connect(root / "state/synthetic.sqlite3")) as db:
        rows = [r[0] for r in db.execute("SELECT phase FROM events ORDER BY id")]
        return (rows == expected and db.execute("PRAGMA integrity_check").fetchone() == ("ok",))


def begin(root: Path, *, crash_at: str | None = None, healthy: bool = False) -> str:
    fd = locked(root)
    try:
        if read_record(root) is not None or active(root) != "baseline":
            raise ValueError("transaction already present or wrong baseline")
        validate_release(root, "baseline")
        validate_release(root, "candidate")
        record(root, "prepared")
        if crash_at == "prepared":
            return "interrupted"
        switch(root, "candidate")
        sync_dir(root)
        record(root, "candidate_selected")
        if crash_at == "candidate_selected":
            return "interrupted"
        record(root, "restart_requested")
        preserve_write(root, "after")
        if crash_at == "restart_requested":
            return "interrupted"
        if healthy:
            record(root, "complete")
            return "candidate_healthy"
        record(root, "health_failed")
        switch(root, "baseline")
        sync_dir(root)
        record(root, "rollback_selected")
        record(root, "recovery_requested")
        record(root, "complete")
        return "rolled_back"
    finally:
        os.close(fd)


def recover(root: Path) -> str:
    fd = locked(root)
    try:
        state = read_record(root)
        if state is None:
            raise ValueError("missing recovery journal")
        if state["phase"] in ("complete", "incident"):
            raise ValueError("completed or incident journal requires operator review")
        validate_release(root, "baseline")
        validate_release(root, "candidate")
        if active(root) not in ("candidate", "baseline"):
            raise ValueError("unexpected active release")
        # This is a disposable code-pointer recovery only; production restart
        # and health verification are NOT modeled by this function.
        if active(root) == "candidate":
            switch(root, "baseline")
            sync_dir(root)
        record(root, "rollback_selected")
        record(root, "recovery_requested")
        record(root, "complete")
        return "baseline_pointer_recovered"
    finally:
        os.close(fd)


def scenario(case: str) -> dict:
    if case not in ("healthy", "failed-health", "crash-prepared",
                    "crash-selected", "crash-restart"):
        raise ValueError("unsupported scenario")
    manager, nav = builder.build()
    with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as temp:
        root = Path(temp)
        make_stage(root, builder.SOURCE.read_bytes(), manager, nav)
        switch(root, "baseline")
        crashes = {"crash-prepared": "prepared", "crash-selected": "candidate_selected",
                   "crash-restart": "restart_requested"}
        initial = begin(root, crash_at=crashes.get(case), healthy=(case == "healthy"))
        if initial == "interrupted":
            outcome = recover(root)
        else:
            outcome = initial
        expected = (["before", "after"] if case in ("healthy", "failed-health", "crash-restart")
                    else ["before"])
        valid = data_preserved(root, expected)
        chosen = active(root)
        if not valid or (chosen != ("candidate" if case == "healthy" else "baseline")):
            raise AssertionError("recovery or SQLite invariant failed")
        return {"scenario": case, "outcome": outcome, "active": chosen,
                "journal": read_record(root)["phase"], "sqlite_preserved": valid}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", choices=("healthy", "failed-health", "crash-prepared",
                                           "crash-selected", "crash-restart"),
                   default="crash-restart")
    args = p.parse_args()
    try:
        report = scenario(args.scenario)
    except (OSError, ValueError, RuntimeError, AssertionError, sqlite3.Error) as exc:
        print("v0.7.1 DURABLE DISPOSABLE TRANSACTION: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 DURABLE DISPOSABLE TRANSACTION: PASS")
    for k, v in report.items():
        print(k + ":", v)
    print("production_executor_available: NO; systemd_modified: NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
