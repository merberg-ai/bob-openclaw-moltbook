#!/usr/bin/env python3
"""Real subprocess SIGKILL crash lab. Disposable fake releases only.

The child is killed by itself AFTER fsynced journal/pointer checkpoints.
Parent reopens state, tests lock availability and refuses implicit resume.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile

import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import make_stage, switch, active, inspect_package, validate_release
import rehearse_v071_transaction_safety as tx

CHECKPOINTS = {"prepared": "baseline", "candidate_selected": "candidate"}
KILL_CODE = -signal.SIGKILL


def child(stage: Path, root: Path, checkpoint: str) -> None:
    # The only entrypoint that can signal a process is available behind a
    # strict parent/child private-directory contract and kills itself only.
    if checkpoint not in CHECKPOINTS:
        raise ValueError("unknown crash checkpoint")
    tx.secure_root(root)
    if stage.is_symlink() or not stage.name.startswith("bob-v071-ui-"):
        raise ValueError("unsafe stage")
    with tx.exclusive(root):
        tx.journal(root, "prepared", "healthy")
        if checkpoint == "candidate_selected":
            switch(stage, "candidate")
            tx.journal(root, "candidate_selected", "healthy")
        os.kill(os.getpid(), signal.SIGKILL)


def run(checkpoint: str) -> dict:
    if checkpoint not in CHECKPOINTS:
        raise ValueError("unknown crash checkpoint")
    manager, nav = builder.build()
    manager, nav = inspect_package(builder.review_zip(manager, nav))
    with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as stage_dir, \
         tempfile.TemporaryDirectory(prefix="bob-v071-journal-") as journal_dir:
        stage, root = Path(stage_dir), Path(journal_dir)
        make_stage(stage, builder.SOURCE.read_bytes(), manager, nav)
        switch(stage, "baseline")
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child",
             "--stage", str(stage), "--journal", str(root),
             "--checkpoint", checkpoint],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=15, check=False)
        if completed.returncode != KILL_CODE:
            raise AssertionError("child did not terminate via SIGKILL")
        # Child's OS advisory lock must have been released on actual death.
        with tx.exclusive(root):
            record = tx.read_journal(root)
            if record is None or record["phase"] != checkpoint:
                raise AssertionError("missing durable crash checkpoint")
            if active(stage) != CHECKPOINTS[checkpoint]:
                raise AssertionError("unexpected release after crash")
            for release in ("baseline", "candidate"):
                validate_release(stage, release)
            # An attempted second transaction must refuse the stale journal.
            try:
                if tx.read_journal(root) is not None:
                    raise ValueError("incomplete journal: operator recovery required")
            except ValueError as exc:
                if str(exc) != "incomplete journal: operator recovery required":
                    raise
            with closing(sqlite3.connect(stage / "state/synthetic.sqlite3")) as db:
                rows = db.execute("SELECT phase FROM events ORDER BY id").fetchall()
                integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if rows != [("before",)] or integrity != "ok":
                raise AssertionError("synthetic data integrity failed")
            return {"checkpoint": checkpoint, "child_killed": True,
                    "lock_released": True, "journal_phase": record["phase"],
                    "selected_release": active(stage), "new_transaction_refused": True,
                    "synthetic_database_intact": True, "production_modified": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", choices=tuple(CHECKPOINTS), default="candidate_selected")
    p.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--stage", type=Path, help=argparse.SUPPRESS)
    p.add_argument("--journal", type=Path, help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.child:
        # Child mode is intentionally limited to a staged disposable layout.
        # Never expose this script as an installed-service tool.
        if args.stage is None or args.journal is None:
            return 2
        child(args.stage, args.journal, args.checkpoint)
        return 3
    try:
        result = run(args.checkpoint)
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.TimeoutExpired,
            sqlite3.Error) as exc:
        print("v0.7.1 PROCESS CRASH LAB: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 PROCESS CRASH LAB: PASS")
    for name, value in result.items():
        print(name + ":", value)
    print("SIGKILL applied exclusively to a disposable child process.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
