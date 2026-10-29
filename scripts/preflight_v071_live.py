#!/usr/bin/env python3
"""Read-only v0.7.1 host readiness preflight. NEVER installs or restarts Bob.

No raw paths, credentials, database rows, or systemd command lines are printed.
This is a gate, not a release authorization or production updater.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import time

EXPECTED_MANAGER_SHA256 = "9f75535bc013c9ea7ab7582e0adfad3e78d6a7ce769a5b14c66b949c5542e65c"
MAX_BACKUP_AGE_SECONDS = 24 * 3600
SERVICE = "bob-activity-manager.service"


def private_regular_file(path: Path, *, max_size: int | None = None) -> bool:
    if not path.is_absolute() or path.is_symlink():
        return False
    try:
        info = path.lstat()
        parent = path.parent.lstat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode) or not stat.S_ISDIR(parent.st_mode):
        return False
    if info.st_uid != os.getuid() or parent.st_uid != os.getuid():
        return False
    if stat.S_IMODE(info.st_mode) & 0o077 or stat.S_IMODE(parent.st_mode) & 0o077:
        return False
    return max_size is None or 0 < info.st_size <= max_size


def check_manager(path: Path) -> bool:
    if not path.is_absolute() or path.is_symlink():
        return False
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 128 * 1024:
            return False
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return False
    return digest == EXPECTED_MANAGER_SHA256


def check_backup(path: Path, now: float | None = None) -> bool:
    if not private_regular_file(path, max_size=1024 * 1024 * 1024):
        return False
    try:
        info = path.stat()
        clock = time.time() if now is None else now
        if not 0 <= clock - info.st_mtime <= MAX_BACKUP_AGE_SECONDS:
            return False
        # An immutable read-only connection, never writes into a real backup.
        uri = path.as_uri() + "?mode=ro&immutable=1"
        with sqlite3.connect(uri, uri=True, timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            return db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    except (OSError, sqlite3.Error, ValueError):
        return False


def check_service() -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", SERVICE,
             "--property=LoadState,ActiveState,SubState", "--no-pager"],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=8, env={**{key: os.environ[key] for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS") if key in os.environ}, "PATH": "/usr/bin:/bin", "LANG": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    lines = result.stdout.splitlines()
    values = {}
    for line in lines:
        if "=" not in line:
            return False
        key, value = line.split("=", 1)
        if key in values or key not in {"LoadState", "ActiveState", "SubState"}:
            return False
        values[key] = value
    return result.returncode == 0 and values == {
        "LoadState": "loaded", "ActiveState": "active", "SubState": "running"
    }


def run(manager: Path, backup: Path, *, now: float | None = None,
        service_check=check_service) -> dict[str, bool]:
    # All checks are observations; the live manager and backup are never modified.
    return {
        "pinned_live_manager": check_manager(manager),
        "recent_private_integrity_checked_backup": check_backup(backup, now=now),
        "activity_manager_service_running": service_check(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-manager", type=Path,
                        default=Path.home() / ".local/bin/bob-activity-manager")
    parser.add_argument("--backup", required=True, type=Path,
                        help="Exact private backup file from backup_live_sqlite.py")
    args = parser.parse_args()
    results = run(args.live_manager.expanduser(), args.backup.expanduser())
    for name, ok in results.items():
        print(name + ":", "PASS" if ok else "REFUSED")
    print("READ-ONLY PREFLIGHT:", "PASS" if all(results.values()) else "REFUSED")
    print("No install, service restart, DB writes, or release switch attempted.")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
