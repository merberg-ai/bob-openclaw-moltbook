#!/usr/bin/env python3
"""Apply only the responsive Settings CSS patch to an exact installed v0.7.2.

Default is read-only. Explicit --apply required. A private backup/journal and
rollback protect this one-file, no-database-change update.
"""
from __future__ import annotations
import argparse
import fcntl
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

import build_v072_settings_candidate as builder
import deploy_v071_activity_manager as service
from rehearse_v071_regular_file_installer import replace_file, fsync_dir

HOME = Path.home()
MANAGER = HOME / ".local/bin/bob-activity-manager"
STATE = HOME / ".local/state/bob-v072-settings-style"
JOURNAL = STATE / "transaction.json"
CONFIRM = "APPLY-BOB-SETTINGS-STYLE"
RECOVER = "RECOVER-BOB-SETTINGS-STYLE"


def versions():
    old, old_nav = builder.build(styled=False)
    new, new_nav = builder.build(styled=True)
    if old_nav != new_nav or old == new:
        raise ValueError("unexpected Settings patch delta")
    return old, new


def private_state():
    if STATE.is_symlink():
        raise ValueError("unsafe patch state directory")
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    s = STATE.stat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o077:
        raise ValueError("unsafe patch state")


def phase():
    if JOURNAL.is_symlink():
        raise ValueError("unsafe patch journal")
    if not JOURNAL.exists():
        return None
    value = json.loads(JOURNAL.read_text())
    if value.get("format") != "bob-v072-style-v1" or value.get("phase") not in (
            "prepared", "switched", "rollback", "complete", "rolled_back", "incident"):
        raise ValueError("unexpected patch journal")
    return value["phase"]


def record(value):
    pending = STATE / ".journal-next"
    if pending.exists() or pending.is_symlink():
        raise ValueError("stale patch journal")
    fd = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(json.dumps({"format": "bob-v072-style-v1", "phase": value}).encode())
        out.flush()
        os.fsync(out.fileno())
    os.replace(pending, JOURNAL)
    fsync_dir(STATE)


def installed_hash():
    if MANAGER.is_symlink() or not MANAGER.is_file():
        raise ValueError("unsafe installed manager")
    return builder.prior.sha256(MANAGER.read_bytes())


def http_ok(auth, styled):
    for route, needle in (("/settings", b"bob-settings-form" if styled else b"Change dashboard password"),
                          ("/", b"v0.7.2")):
        conn = HTTPConnection("127.0.0.1", 18790, timeout=4)
        try:
            conn.request("GET", route, headers={
                "Host": "127.0.0.1:18790", "Authorization": auth})
            result = conn.getresponse()
            data = result.read(262144)
            if result.status != 200 or needle not in data:
                return False
        except (OSError, TimeoutError):
            return False
        finally:
            conn.close()
    return True


def healthy(auth, styled):
    for i in range(7):
        if service.service_active() and http_ok(auth, styled):
            return True
        if i < 6:
            time.sleep(0.5)
    return False


def rollback(old, new, auth):
    h = installed_hash()
    if h not in (builder.prior.sha256(old), builder.prior.sha256(new)):
        record("incident")
        raise ValueError("installed manager differs from pinned expected bytes")
    record("rollback")
    if h != builder.prior.sha256(old):
        replace_file(MANAGER, old, builder.prior.sha256(new), 0o700)
    try:
        service.service("restart")
        if installed_hash() != builder.prior.sha256(old) or not healthy(auth, False):
            raise RuntimeError("baseline recovery failed")
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        record("incident")
        raise
    record("rolled_back")
    return "original_settings_restored"


def operate(recover=False):
    old, new = versions()
    auth = service.authenticate()
    private_state()
    lock = os.open(STATE / "transaction.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status = phase()
        if recover:
            if status is None or status in ("complete", "rolled_back", "incident"):
                raise ValueError("no recoverable incomplete patch")
            old_file = STATE / "manager-before"
            if old_file.is_symlink() or not old_file.is_file() or old_file.read_bytes() != old:
                raise ValueError("private patch rollback snapshot changed")
            return rollback(old, new, auth)
        if status is not None:
            raise ValueError("existing patch journal")
        if installed_hash() != builder.prior.sha256(old):
            raise ValueError("live installed manager differs from exact v0.7.2")
        if not healthy(auth, False):
            raise ValueError("existing dashboard is not healthy")
        snapshot = STATE / "manager-before"
        fd = os.open(snapshot, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as backup:
            backup.write(old)
            backup.flush()
            os.fsync(backup.fileno())
        fsync_dir(STATE)
        record("prepared")
        try:
            replace_file(MANAGER, new, builder.prior.sha256(old), 0o700)
            record("switched")
            service.service("restart")
            if installed_hash() != builder.prior.sha256(new) or not healthy(auth, True):
                raise RuntimeError("updated Settings page failed verification")
            record("complete")
            return "settings_style_updated"
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            rollback(old, new, auth)
            return "rolled_back"
    finally:
        os.close(lock)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--recover", action="store_true")
    p.add_argument("--confirm", default="")
    args = p.parse_args()
    if os.geteuid() == 0:
        p.error("refusing root")
    try:
        if not args.apply and not args.recover:
            old, new = versions()
            current = installed_hash()
            print("v0.7.2 SETTINGS STYLE PATCH:",
                  "READY" if current == builder.prior.sha256(old) else "NOT READY")
            print("production_modified: NO")
            return 0 if current == builder.prior.sha256(old) else 1
        needed = RECOVER if args.recover else CONFIRM
        if args.confirm != needed:
            raise ValueError("confirmation required")
        result = operate(recover=args.recover)
        print("v0.7.2 SETTINGS STYLE PATCH:", result)
        return 0 if result == "settings_style_updated" or result == "original_settings_restored" else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("v0.7.2 SETTINGS STYLE PATCH: REFUSED", type(exc).__name__)
        print("Do not retry a failed patch before reviewing the private journal.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
