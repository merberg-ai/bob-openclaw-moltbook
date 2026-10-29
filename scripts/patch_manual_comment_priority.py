#!/usr/bin/env python3
"""One-file guarded manual-first publisher queue release.

Default is read-only. --apply requires confirmation. Does not start workers,
submit comments, change queue state or alter posting limits. Existing one-shot
workers finish with their loaded code; next invocation uses the new policy.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from backup_live_sqlite import create_verified_backup
from rehearse_v071_regular_file_installer import replace_file, fsync_dir

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
LIVE = HOME / ".local/bin/bob-moltbook-publisher"
OLD = ROOT / "release_baselines/v072-manual-priority/bob-moltbook-publisher"
NEW = ROOT / "release_baselines/v072-manual-priority/after-bob-moltbook-publisher"
STATE = HOME / ".local/state/bob-v072-manual-priority"
JOURNAL = STATE / "transaction.json"
DB = HOME / ".config/moltbook/activity-queue.sqlite3"
BACKUPS = HOME / ".local/state/bob-baseline/backups"
FORMAT = "bob-v072-manual-priority-v1"
CONFIRM = "UPGRADE-BOB-MANUAL-PRIORITY"
RECOVER = "RECOVER-BOB-MANUAL-PRIORITY"


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def releases():
    if OLD.is_symlink() or NEW.is_symlink() or not OLD.is_file() or not NEW.is_file():
        raise ValueError("unsafe release source")
    old, new = OLD.read_bytes(), NEW.read_bytes()
    if old == new:
        raise ValueError("unchanged release")
    compile(old, str(OLD), "exec")
    compile(new, str(NEW), "exec")
    expected = b"ORDER BY created_at ASC LIMIT 1"
    preferred = b"ORDER BY CASE WHEN mode='manual' THEN 0 ELSE 1 END, created_at ASC, run_id ASC LIMIT 1"
    if old.count(expected) != 1 or new.count(preferred) != 1:
        raise ValueError("unrecognized publisher queue ordering")
    # This release is intentionally ONLY the queue ordering SQL and its comment.
    previous = old.decode("utf-8")
    changed = new.decode("utf-8")
    insert = """    # Manual approvals outrank auto drafts. A held/disabled auto item must not
    # starve a newer human-approved reply; rate limits and checks still apply.
"""
    if changed.count(insert) != 1:
        raise ValueError("unexpected source delta")
    changed = changed.replace(insert, "", 1).replace(preferred.decode(), expected.decode(), 1)
    if changed != previous:
        raise ValueError("publisher contains unrelated changes")
    return old, new


def state_dir():
    if STATE.is_symlink():
        raise ValueError("unsafe state directory")
    STATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    s = STATE.stat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o077:
        raise ValueError("unprivate state directory")


def phase():
    if JOURNAL.is_symlink():
        raise ValueError("unsafe transaction journal")
    if not JOURNAL.exists():
        return None
    if not JOURNAL.is_file() or JOURNAL.stat().st_size > 512:
        raise ValueError("malformed transaction journal")
    value = json.loads(JOURNAL.read_text())
    if value.get("format") != FORMAT or value.get("phase") not in (
            "prepared", "installed", "complete", "rolling_back", "rolled_back", "incident"):
        raise ValueError("unrecognized transaction journal")
    return value["phase"]


def record(value):
    pending = STATE / ".next-journal"
    if pending.exists() or pending.is_symlink():
        raise ValueError("stale journal staging file")
    fd = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(json.dumps({"format": FORMAT, "phase": value}).encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, JOURNAL)
    fsync_dir(STATE)


def current(data):
    return (not LIVE.is_symlink() and LIVE.is_file() and
            LIVE.stat().st_uid == os.getuid() and
            not stat.S_IMODE(LIVE.stat().st_mode) & 0o022 and
            digest(LIVE.read_bytes()) == digest(data))


def rollback(old, new):
    if not current(old) and not current(new):
        record("incident")
        raise ValueError("installed publisher changed unexpectedly")
    record("rolling_back")
    if current(new):
        replace_file(LIVE, old, digest(new), 0o700)
    if not current(old):
        record("incident")
        raise RuntimeError("publisher rollback verification failed")
    record("rolled_back")
    return "baseline_restored"


def apply(recover=False):
    old, new = releases()
    state_dir()
    fd = os.open(STATE / "transaction.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError("unsafe transaction lock")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status = phase()
        if recover:
            if status not in ("prepared", "installed", "rolling_back"):
                raise ValueError("no recoverable interrupted operation")
            before = STATE / "publisher-before"
            if before.is_symlink() or not before.is_file() or before.read_bytes() != old:
                raise ValueError("private baseline changed")
            return rollback(old, new)
        if status is not None:
            raise ValueError("existing release transaction")
        if not current(old):
            raise ValueError("live publisher differs from pinned baseline")
        # Backup protects queue history without altering live SQLite.
        create_verified_backup(DB, BACKUPS)
        before = STATE / "publisher-before"
        backup_fd = os.open(before, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(backup_fd, "wb") as output:
            output.write(old)
            output.flush()
            os.fsync(output.fileno())
        fsync_dir(STATE)
        record("prepared")
        try:
            replace_file(LIVE, new, digest(old), 0o700)
            record("installed")
            if not current(new):
                raise RuntimeError("publisher file failed hash verification")
            record("complete")
            return "manual_priority_installed"
        except (OSError, ValueError, RuntimeError):
            return rollback(old, new)
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
            old, new = releases()
            ready = current(old)
            print("MANUAL-PRIORITY READINESS:", "PASS" if ready else "REFUSED")
            print("production_modified: NO")
            return 0 if ready else 1
        required = RECOVER if args.recover else CONFIRM
        if args.confirm != required:
            raise ValueError("explicit confirmation required")
        result = apply(recover=args.recover)
        print("MANUAL-PRIORITY UPDATE:", result)
        return 0 if result in ("baseline_restored", "manual_priority_installed") else 1
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print("MANUAL-PRIORITY UPDATE: REFUSED", type(exc).__name__)
        print("Inspect the private transaction journal before retrying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
