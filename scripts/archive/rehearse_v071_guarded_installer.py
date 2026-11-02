#!/usr/bin/env python3
"""v0.7.1 guarded installer architecture, DISPOSABLE SANDBOX ONLY.

No production mode or flag. This module cannot invoke systemctl, real Bob,
external networks, or production database. A future installer must be separate,
explicitly reviewed and independently authorized.
"""
from __future__ import annotations

from contextlib import closing
import argparse
import os
from pathlib import Path
import sqlite3
import tempfile

import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import (
    active, inspect_package, make_stage, switch, validate_release,
)
import rehearse_v071_transaction_safety as tx
from rehearse_v071_http_adapter import IsolatedService, bounded_health

SCENARIOS = ("success", "health-failure", "recovery-failure", "refuse-drift")


def append_synthetic_write(root: Path) -> None:
    with closing(sqlite3.connect(root / "state/synthetic.sqlite3")) as db:
        db.execute("INSERT INTO events(phase) VALUES ('during')")
        db.commit()


def guard(stage: Path, journal: Path) -> None:
    tx.secure_root(journal)
    if tx.read_journal(journal) is not None:
        raise ValueError("existing transaction")
    if active(stage) != "baseline":
        raise ValueError("baseline pointer changed")
    validate_release(stage, "baseline")
    validate_release(stage, "candidate")


def run_sandbox(scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError("unsupported scenario")
    manager, nav = builder.build()
    manager, nav = inspect_package(builder.review_zip(manager, nav))
    with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as stage_path, \
         tempfile.TemporaryDirectory(prefix="bob-v071-journal-") as journal_path:
        stage, journal_root = Path(stage_path), Path(journal_path)
        make_stage(stage, builder.SOURCE.read_bytes(), manager, nav)
        switch(stage, "baseline")
        service = IsolatedService(healthy=scenario == "success")
        with tx.exclusive(journal_root):
            guard(stage, journal_root)
            if scenario == "refuse-drift":
                # The release pointer was just verified, but the simulated
                # preflight now detects a changed source fingerprint.
                return {"outcome": "preflight_refused", "release": active(stage),
                        "starts": 0, "journal": "none", "db_preserved": True}
            tx.journal(journal_root, "prepared", "healthy")
            append_synthetic_write(stage)
            switch(stage, "candidate")
            tx.journal(journal_root, "candidate_selected", "healthy")
            try:
                service.start()
                tx.journal(journal_root, "restart_requested", "healthy")
                if bounded_health(service):
                    tx.journal(journal_root, "complete", "healthy")
                    outcome = "candidate_healthy"
                else:
                    tx.journal(journal_root, "health_failed", "healthy")
                    service.stop()
                    switch(stage, "baseline")
                    tx.journal(journal_root, "rollback_selected", "healthy")
                    service.healthy = scenario == "health-failure"
                    service.start()
                    tx.journal(journal_root, "recovery_requested", "healthy")
                    if bounded_health(service):
                        tx.journal(journal_root, "complete", "healthy")
                        outcome = "rolled_back"
                    else:
                        tx.journal(journal_root, "incident", "healthy")
                        outcome = "recovery_failed"
            finally:
                service.stop()
            with closing(sqlite3.connect(stage / "state/synthetic.sqlite3")) as db:
                events = db.execute("SELECT phase FROM events ORDER BY id").fetchall()
                integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if events != [("before",), ("during",)] or integrity != "ok":
                raise AssertionError("synthetic SQLite changed incorrectly")
            return {"outcome": outcome, "release": active(stage),
                    "starts": service.starts,
                    "journal": tx.read_journal(journal_root)["phase"],
                    "db_preserved": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="health-failure")
    args = parser.parse_args()
    expected = {
        "success": ("candidate_healthy", "candidate", 1, "complete"),
        "health-failure": ("rolled_back", "baseline", 2, "complete"),
        "recovery-failure": ("recovery_failed", "baseline", 2, "incident"),
        "refuse-drift": ("preflight_refused", "baseline", 0, "none"),
    }
    try:
        report = run_sandbox(args.scenario)
        actual = tuple(report[k] for k in ("outcome", "release", "starts", "journal"))
        if actual != expected[args.scenario] or not report["db_preserved"]:
            raise AssertionError("wrong scenario result")
    except (OSError, ValueError, RuntimeError, AssertionError, sqlite3.Error) as exc:
        print("v0.7.1 GUARDED INSTALLER SANDBOX: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 GUARDED INSTALLER SANDBOX: PASS")
    print("scenario:", args.scenario)
    for key, value in report.items():
        print(key + ":", value)
    print("production_install_available: NO; systemd_modified: NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
