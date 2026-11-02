#!/usr/bin/env python3
"""Guarded v0.7.2 worker-stage tracking completion, from a pinned live baseline.

Default is read-only. Explicit --apply, automatic verified SQLite backup,
private journal, atomic code replacements and rollback on failed HTTP health.
No schema changes, publishing operations, or changes to consent/auto mode.
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
import time

import build_v072_live_candidate as baseline_builder
import deploy_v071_activity_manager as services
from backup_live_sqlite import create_verified_backup
from rehearse_v071_regular_file_installer import replace_file, fsync_dir

HOME = Path.home()
BIN = HOME / ".local/bin"
ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "release_baselines/v072-tracking"
SOURCE = ROOT / "src"
STATE = HOME / ".local/state/bob-v072-tracking-update"
JOURNAL = STATE / "transaction.json"
DB = HOME / ".config/moltbook/activity-queue.sqlite3"
BACKUPS = HOME / ".local/state/bob-baseline/backups"
FILES = ("bob_live_status.py", "bob_status_view.py", "bob-moltbook-scout",
         "bob-moltbook-publisher", "bob-original-worker")
ADD = "bob_job_tracking.py"
ALL = (ADD,) + FILES
TOKEN = "UPGRADE-BOB-JOB-TRACKING"
RECOVERY_TOKEN = "RECOVER-BOB-JOB-TRACKING"
FORMAT = "bob-v072-job-tracking-v1"
PHASES = {"prepared", "installed", "restarted", "rolling_back",
          "complete", "rolled_back", "incident"}


def hash_bytes(data):
    return baseline_builder.current.prior.sha256(data)


def versions():
    before = {}
    after = {}
    for name in FILES:
        old = PREVIOUS / name
        new = (SOURCE / "lib/bob" / name) if name.endswith(".py") else (SOURCE / "bin" / name)
        for item in (old, new):
            if item.is_symlink() or not item.is_file():
                raise ValueError("unsafe release source")
        before[name] = old.read_bytes()
        after[name] = new.read_bytes()
        compile(after[name], name, "exec")
    source = SOURCE / "lib/bob" / ADD
    if source.is_symlink() or not source.is_file():
        raise ValueError("tracking module missing")
    after[ADD] = source.read_bytes()
    compile(after[ADD], ADD, "exec")
    manager, _ = baseline_builder.build()
    return before, after, hash_bytes(manager)


def mode(name):
    return 0o700 if name in ("bob-moltbook-scout", "bob-moltbook-publisher", "bob-original-worker") else 0o600


def safe_state():
    if STATE.is_symlink():
        raise ValueError("unsafe state folder")
    STATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = STATE.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("unprivate state folder")


def transaction():
    if JOURNAL.is_symlink():
        raise ValueError("unsafe journal")
    if not JOURNAL.exists():
        return None
    if not JOURNAL.is_file() or JOURNAL.stat().st_size > 512:
        raise ValueError("invalid journal")
    v = json.loads(JOURNAL.read_text())
    if set(v) != {"format", "phase"} or v["format"] != FORMAT or v["phase"] not in PHASES:
        raise ValueError("unexpected transaction journal")
    return v["phase"]


def record(phase):
    if phase not in PHASES:
        raise ValueError("bad transaction phase")
    pending = STATE / ".transaction-next"
    if pending.exists() or pending.is_symlink():
        raise ValueError("pending transaction residue")
    fd = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(json.dumps({"format": FORMAT, "phase": phase}, sort_keys=True).encode())
        output.flush()
        os.fsync(output.fileno())
    os.replace(pending, JOURNAL)
    fsync_dir(STATE)


def locked():
    safe_state()
    fd = os.open(STATE / "transaction.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
        os.close(fd)
        raise ValueError("unsafe transaction lock")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def matched(before, after, manager_sha, upgraded):
    manager = BIN / "bob-activity-manager"
    if manager.is_symlink() or not manager.is_file() or hash_bytes(manager.read_bytes()) != manager_sha:
        return False
    values = after if upgraded else before
    for name, content in values.items():
        path = BIN / name
        if path.is_symlink() or not path.is_file():
            return False
        info = path.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            return False
        if hash_bytes(path.read_bytes()) != hash_bytes(content):
            return False
    if not upgraded and ((BIN / ADD).exists() or (BIN / ADD).is_symlink()):
        return False
    return True


def probe(auth, upgraded):
    for route in ("/healthz", "/settings", "/system/status", "/api/system/status"):
        connection = HTTPConnection("127.0.0.1", 18790, timeout=18 if "status" in route else 4)
        try:
            connection.request("GET", route, headers={"Host": "127.0.0.1:18790", "Authorization": auth})
            response = connection.getresponse()
            payload = response.read(262145)
            if response.status != 200 or len(payload) > 262144:
                return False
            if route == "/healthz" and json.loads(payload).get("ok") is not True:
                return False
            if route == "/settings" and b"bob-settings-form" not in payload:
                return False
            if route == "/system/status" and (b"bob-worker-grid" in payload) != upgraded:
                return False
            if route == "/api/system/status":
                data = json.loads(payload)
                if not isinstance(data.get("queue"), dict) or not isinstance(data.get("services"), list):
                    return False
                if upgraded and not isinstance(data.get("workers"), list):
                    return False
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
            return False
        finally:
            connection.close()
    return True


def healthy(auth, upgraded):
    for attempt in range(7):
        if services.service_active() and probe(auth, upgraded):
            return True
        if attempt < 6:
            time.sleep(0.6)
    return False


def archive(before):
    for name, content in before.items():
        path = STATE / ("before-" + name)
        if path.exists() or path.is_symlink():
            raise ValueError("baseline backup already exists")
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
    fsync_dir(STATE)


def rollback(before, after, manager_sha, auth):
    for name in ALL:
        target = BIN / name
        if target.is_symlink():
            raise ValueError("rollback symlink")
        if name in before:
            if not target.is_file() or target.read_bytes() not in (before[name], after[name]):
                raise ValueError("unexpected installed file: manual intervention required")
        elif target.exists() and (not target.is_file() or target.read_bytes() != after[name]):
            raise ValueError("unknown added file")
    record("rolling_back")
    for name, content in before.items():
        path = BIN / name
        if path.read_bytes() != content:
            replace_file(path, content, hash_bytes(after[name]), mode(name))
    added = BIN / ADD
    if added.exists():
        added.unlink()
        fsync_dir(BIN)
    services.service("restart")
    if not matched(before, after, manager_sha, False) or not healthy(auth, False):
        record("incident")
        raise RuntimeError("original dashboard recovery failed")
    record("rolled_back")
    return "baseline_restored"


def perform(recover=False):
    before, after, manager_sha = versions()
    fd = locked()
    try:
        phase = transaction()
        if recover:
            if phase not in ("prepared", "installed", "restarted", "rolling_back"):
                raise ValueError("no interrupted transaction to recover")
            for name, data in before.items():
                backup = STATE / ("before-" + name)
                if backup.is_symlink() or not backup.is_file() or backup.read_bytes() != data:
                    raise ValueError("private recovery file mismatch")
            return rollback(before, after, manager_sha, services.authenticate())
        if phase is not None:
            raise ValueError("existing update transaction")
        if not matched(before, after, manager_sha, False):
            raise ValueError("installed v0.7.2 code differs from pinned baseline")
        auth = services.authenticate()
        if not healthy(auth, False):
            raise ValueError("installed dashboard HTTP unhealthy")
        create_verified_backup(DB, BACKUPS)
        archive(before)
        record("prepared")
        try:
            for name in ALL:
                replace_file(BIN / name, after[name],
                             hash_bytes(before[name]) if name in before else None, mode(name))
            record("installed")
            services.service("restart")
            record("restarted")
            if not matched(before, after, manager_sha, True) or not healthy(auth, True):
                raise RuntimeError("job-tracking release health refused")
            record("complete")
            return "job_tracking_installed"
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            try:
                rollback(before, after, manager_sha, auth)
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
                record("incident")
                raise RuntimeError("rollback incident; inspect private journal") from None
            return "rolled_back"
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--recover", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run as openclaw, not root")
    try:
        if not args.apply and not args.recover:
            before, after, manager = versions()
            ok = matched(before, after, manager, False)
            print("v0.7.2 TRACKING READINESS:", "PASS" if ok else "REFUSED")
            print("production_modified: NO")
            return 0 if ok else 1
        if args.confirm != (RECOVERY_TOKEN if args.recover else TOKEN):
            raise ValueError("explicit confirmation required")
        result = perform(recover=args.recover)
        print("v0.7.2 TRACKING:", result)
        return 0 if result in ("job_tracking_installed", "baseline_restored") else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print("v0.7.2 TRACKING: REFUSED", type(exc).__name__)
        print("If an update started, review the private journal before retrying.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
