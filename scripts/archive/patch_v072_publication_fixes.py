#!/usr/bin/env python3
"""Guarded v0.7.2 publication-truth and original-draft parser hotfix.

Default is read-only. Explicit --apply requires confirmation, creates a verified
SQLite backup, exact-matches installed code, journals old files privately,
updates only three modules and the dashboard, checks authenticated HTTP, and
restores original code on failure. No automatic publishing or retries.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import stat
import subprocess
import time

import build_v072_live_candidate as old_builder
import build_v072_publication_truth_candidate as new_builder
import deploy_v071_activity_manager as svc
from backup_live_sqlite import create_verified_backup
from rehearse_v071_regular_file_installer import replace_file, fsync_dir

HOME = Path.home()
ROOT = Path(__file__).resolve().parents[1]
BIN = HOME / ".local/bin"
STATE = HOME / ".local/state/bob-v072-publication-fix"
JOURNAL = STATE / "transaction.json"
DB = HOME / ".config/moltbook/activity-queue.sqlite3"
BACKUPS = HOME / ".local/state/bob-baseline/backups"
PREVIOUS = ROOT / "release_baselines/v072-pubfix"
FILES = ("bob-activity-manager", "bob-moltbook-publisher",
         "bob-original-worker", "bob_live_status.py")
CONFIRM = "UPGRADE-BOB-PUBLICATION-FIX"
RECOVER = "RECOVER-BOB-PUBLICATION-FIX"
FORMAT = "bob-v072-publication-fix-v1"
PHASES = {"prepared", "installed", "restarted", "rolling_back",
          "complete", "rolled_back", "incident"}


def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()


def versions():
    manager_old, nav_old = old_builder.build()
    manager_new, nav_new = new_builder.build()
    if manager_old == manager_new or nav_old != nav_new:
        raise ValueError("unexpected manager release change")
    old = {"bob-activity-manager": manager_old}
    new = {"bob-activity-manager": manager_new}
    for name in FILES[1:]:
        baseline = PREVIOUS / name
        candidate = ((ROOT / "src/lib/bob" / name) if name.endswith(".py")
                     else (ROOT / "src/bin" / name))
        for path in (baseline, candidate):
            if path.is_symlink() or not path.is_file():
                raise ValueError("missing or unsafe release source")
        old[name] = baseline.read_bytes()
        new[name] = candidate.read_bytes()
        compile(new[name], name, "exec")
        if old[name] == new[name]:
            raise ValueError("unchanged module in requested release")
    return old, new


def ensure_state():
    if STATE.is_symlink():
        raise ValueError("unsafe state folder")
    STATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = STATE.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("unprivate state folder")


def existing_journal():
    if JOURNAL.is_symlink():
        raise ValueError("unsafe journal")
    if not JOURNAL.exists():
        return None
    if not JOURNAL.is_file() or JOURNAL.stat().st_size > 512:
        raise ValueError("invalid journal")
    data = json.loads(JOURNAL.read_text())
    if set(data) != {"format", "phase"} or data["format"] != FORMAT or data["phase"] not in PHASES:
        raise ValueError("unexpected journal")
    return data["phase"]


def record(phase):
    if phase not in PHASES:
        raise ValueError("invalid journal phase")
    pending = STATE / ".journal-next"
    if pending.exists() or pending.is_symlink():
        raise ValueError("stale pending journal")
    fd = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(json.dumps({"format": FORMAT, "phase": phase}, sort_keys=True).encode())
        output.flush()
        os.fsync(output.fileno())
    os.replace(pending, JOURNAL)
    fsync_dir(STATE)


def acquire():
    ensure_state()
    fd = os.open(STATE / "transaction.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
        os.close(fd)
        raise ValueError("unsafe lock")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def installed(expected):
    for name, content in expected.items():
        path = BIN / name
        if path.is_symlink() or not path.is_file():
            return False
        statinfo = path.stat()
        if statinfo.st_uid != os.getuid() or stat.S_IMODE(statinfo.st_mode) & 0o022:
            return False
        if digest(path.read_bytes()) != digest(content):
            return False
    return True


def http_ok(auth, upgraded):
    for route in ("/healthz", "/settings", "/activity", "/system/status", "/api/system/status"):
        conn = HTTPConnection("127.0.0.1", 18790, timeout=18 if "status" in route else 5)
        try:
            conn.request("GET", route, headers={"Host": "127.0.0.1:18790", "Authorization": auth})
            resp = conn.getresponse()
            content = resp.read(262145)
            if resp.status != 200 or len(content) > 262144:
                return False
            if route == "/healthz" and json.loads(content).get("ok") is not True:
                return False
            if route == "/settings" and b"bob-settings-form" not in content:
                return False
            if route == "/activity":
                if (b"Comments without confirmed IDs" in content) != upgraded:
                    return False
            if route == "/api/system/status":
                data = json.loads(content)
                if not isinstance(data.get("queue"), dict) or not isinstance(data.get("workers"), list):
                    return False
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
            return False
        finally:
            conn.close()
    return True


def healthy(auth, upgraded):
    for attempt in range(7):
        if svc.service_active() and http_ok(auth, upgraded):
            return True
        if attempt < 6:
            time.sleep(0.6)
    return False


def archive(previous):
    for name, content in previous.items():
        path = STATE / ("before-" + name)
        if path.is_symlink() or path.exists():
            raise ValueError("existing private backup")
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as backup:
            backup.write(content)
            backup.flush()
            os.fsync(backup.fileno())
    fsync_dir(STATE)


def rollback(previous, candidate, auth):
    for name in FILES:
        path = BIN / name
        if path.is_symlink() or not path.is_file() or path.read_bytes() not in (previous[name], candidate[name]):
            raise ValueError("unknown installed code; refuse automatic rollback")
    record("rolling_back")
    for name in FILES:
        path = BIN / name
        if path.read_bytes() != previous[name]:
            replace_file(path, previous[name], digest(candidate[name]),
                         0o700 if name != "bob_live_status.py" else 0o600)
    try:
        svc.service("restart")
        if not installed(previous) or not healthy(auth, False):
            raise RuntimeError("baseline HTTP recovery failed")
        record("rolled_back")
        return "baseline_restored"
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        record("incident")
        raise


def operate(recover=False):
    previous, candidate = versions()
    lockfd = acquire()
    try:
        phase = existing_journal()
        if recover:
            if phase not in ("prepared", "installed", "restarted", "rolling_back"):
                raise ValueError("no recoverable interrupted update")
            for name, expected in previous.items():
                file = STATE / ("before-" + name)
                if file.is_symlink() or not file.is_file() or file.read_bytes() != expected:
                    raise ValueError("private backup mismatch")
            return rollback(previous, candidate, svc.authenticate())
        if phase is not None:
            raise ValueError("previous release transaction exists")
        if not installed(previous):
            raise ValueError("installed code differs from approved baseline")
        auth = svc.authenticate()
        if not healthy(auth, False):
            raise ValueError("baseline HTTP unhealthy")
        create_verified_backup(DB, BACKUPS)
        archive(previous)
        record("prepared")
        try:
            for name in FILES:
                replace_file(BIN / name, candidate[name], digest(previous[name]),
                             0o700 if name != "bob_live_status.py" else 0o600)
            record("installed")
            svc.service("restart")
            record("restarted")
            if not installed(candidate) or not healthy(auth, True):
                raise RuntimeError("publication fix HTTP unhealthy")
            record("complete")
            return "publication_fixes_installed"
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            try:
                rollback(previous, candidate, auth)
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
                record("incident")
                raise RuntimeError("rollback incident; inspect private journal") from None
            return "rolled_back"
    finally:
        os.close(lockfd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--recover", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run as openclaw, not root")
    try:
        if not args.apply and not args.recover:
            previous, candidate = versions()
            ready = installed(previous)
            print("v0.7.2 PUBLICATION FIX READINESS:", "PASS" if ready else "REFUSED")
            print("production_modified: NO")
            return 0 if ready else 1
        expected = RECOVER if args.recover else CONFIRM
        if args.confirm != expected:
            raise ValueError("explicit approval required")
        result = operate(recover=args.recover)
        print("v0.7.2 PUBLICATION FIX:", result)
        return 0 if result in ("publication_fixes_installed", "baseline_restored") else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print("v0.7.2 PUBLICATION FIX: REFUSED", type(exc).__name__)
        print("If transaction started, inspect private journal before any retry.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
