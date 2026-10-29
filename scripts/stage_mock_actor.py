#!/usr/bin/env python3
"""Inert Bob staging fixture. No imports of Bob, systemctl, network or publishing.

Only runs inside a fresh private test sandbox made by stage_service_graph.py.
Never accepts a configurable database path, remote URL or executable program.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import stat
import sys
import time

MARKER = "bob-v070-inert-service-sandbox"
ROLES = {"gateway", "manager", "scout", "publisher", "original-worker", "reconcile"}
MOCK_CONFIG = {"purpose": MARKER, "network_access": False, "allow_publish": False,
               "credential": "DUMMY-NONFUNCTIONAL-ONLY"}


def validate(root: Path) -> tuple[Path, str]:
    if root.is_symlink() or not root.is_absolute():
        raise ValueError("Sandbox must be an absolute, non-symlink path")
    root = root.resolve(strict=True)
    if root.name.startswith(".") or not root.name.startswith("bob-v070-stage-"):
        raise ValueError("Refusing non-staging root")
    if root == Path.home() or not root.is_dir():
        raise ValueError("Not an isolated staging directory")
    if stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise ValueError("Sandbox root must be private")
    marker = root / "STAGING-MARKER.json"
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("Missing staging marker")
    meta = json.loads(marker.read_text(encoding="utf-8"))
    if meta != {"purpose": MARKER, "production_allowed": False}:
        raise ValueError("Incorrect staging marker")
    config = root / "private" / "MOCK-CONFIG.json"
    if (config.is_symlink() or not config.is_file()
            or stat.S_IMODE(config.stat().st_mode) & 0o077):
        raise ValueError("Missing or insecure mock configuration")
    if json.loads(config.read_text(encoding="utf-8")) != MOCK_CONFIG:
        raise ValueError("Only explicitly offline dummy configuration is accepted")
    current = root / "current"
    if not current.is_symlink():
        raise ValueError("Missing staging release pointer")
    ref = os.readlink(current)
    if ref not in {"releases/baseline", "releases/candidate"}:
        raise ValueError("Unexpected staging release pointer")
    release = ref.split("/")[-1]
    base = root / "releases" / release
    if not base.is_dir() or base.is_symlink():
        raise ValueError("Missing staging release")
    database = root / "private" / "synthetic.sqlite3"
    if (database.is_symlink() or not database.is_file()
            or stat.S_IMODE(database.stat().st_mode) & 0o077):
        raise ValueError("Missing or insecure synthetic database")
    return database, release


def run_once(root: Path, role: str) -> str:
    if role not in ROLES:
        raise ValueError("Unknown mock role")
    database, release = validate(root)
    # The complete schema is synthetic and independent of real Bob tables.
    with sqlite3.connect(database, timeout=2) as db:
        db.execute("INSERT INTO simulated_events (role, release_tag) VALUES (?, ?)",
                   (role, release))
        db.commit()
    return release


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", type=Path, required=True)
    parser.add_argument("--role", required=True, choices=sorted(ROLES))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Refusing root user")
    try:
        release = run_once(args.stage_root, args.role)
        if args.serve:
            # A mock long-running unit waits only: no socket bind, worker,
            # timer dispatch, external process, or periodic remote requests.
            while True:
                time.sleep(30)
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print("INERT STAGING ACTOR REFUSED:", type(exc).__name__,
              "(production untouched)", file=sys.stderr)
        return 1
    print("Mock role completed:", args.role, "release:", release)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
