#!/usr/bin/env python3
"""One-command, version-pinned v0.7.1 -> v0.7.2 Activity Manager upgrade.

Default: read-only readiness check. --apply requires explicit confirmation.
Creates a verified PRIVATE SQLite backup automatically. No DB writes, workers
or publishing actions. A private journal and locked code rollback guard changes.
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
import tempfile
import time

import build_v071_manager_candidate as previous
import build_v072_settings_candidate as next_release
import deploy_v071_activity_manager as service_helper
from backup_live_sqlite import create_verified_backup
from preflight_v071_effective_service import classify, query
from rehearse_v071_regular_file_installer import replace_file, fsync_dir

HOME = Path.home()
BIN = HOME / ".local/bin"
STATE = HOME / ".local/state/bob-v072-deploy"
JOURNAL = STATE / "transaction.json"
LOCK = STATE / "transaction.lock"
DB = HOME / ".config/moltbook/activity-queue.sqlite3"
BACKUPS = HOME / ".local/state/bob-baseline/backups"
FILE_MODES = {"bob-activity-manager": 0o700, "navigation_shell.py": 0o600,
              "bob_dashboard_auth.py": 0o600, "bob_live_status.py": 0o600}
PHASES = {"prepared", "files_installed", "restart_requested",
          "rollback_started", "recovery_requested", "complete", "rolled_back", "incident"}
CONFIRM = "UPGRADE-BOB-V072"
RECOVER = "RECOVER-BOB-V072"
MANIFEST = "bob-v072-regular-files-v1"


def digest(content: bytes):
    return previous.sha256(content)


def releases():
    old_mgr, old_nav = previous.build()
    new_mgr, new_nav = next_release.build()
    files_old = {"bob-activity-manager": old_mgr, "navigation_shell.py": old_nav}
    files_new = {"bob-activity-manager": new_mgr, "navigation_shell.py": new_nav}
    for name in ("bob_dashboard_auth.py", "bob_live_status.py"):
        source = previous.HERE / "src/lib/bob" / name
        if source.is_symlink() or not source.is_file():
            raise ValueError("missing or unsafe module source")
        content = source.read_bytes()
        compile(content, name, "exec")
        files_new[name] = content
    return files_old, files_new


def safe_dir(path: Path):
    if path.is_symlink():
        raise ValueError("unsafe state directory")
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    st = path.stat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
        raise ValueError("state directory not private")


def atomic_private(path: Path, data: bytes):
    if path.is_symlink():
        raise ValueError("symlink refused")
    fd, tempname = tempfile.mkstemp(prefix=".v072-pending-", dir=path.parent)
    temp = Path(tempname)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        fsync_dir(path.parent)
    finally:
        temp.unlink(missing_ok=True)


def record(phase: str):
    if phase not in PHASES:
        raise ValueError("invalid journal phase")
    atomic_private(JOURNAL, json.dumps({"format": MANIFEST, "phase": phase},
                                       sort_keys=True).encode())


def state():
    if JOURNAL.is_symlink():
        raise ValueError("unsafe journal")
    if not JOURNAL.exists():
        return None
    if not JOURNAL.is_file() or JOURNAL.stat().st_size > 512:
        raise ValueError("malformed journal")
    value = json.loads(JOURNAL.read_text())
    if set(value) != {"format", "phase"} or value["format"] != MANIFEST or value["phase"] not in PHASES:
        raise ValueError("unexpected journal")
    return value["phase"]


def hold_lock():
    safe_dir(STATE)
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
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


def installed_matches(content_by_name, absent):
    for name, data in content_by_name.items():
        p = BIN / name
        if p.is_symlink() or not p.is_file():
            return False
        st = p.stat()
        if (st.st_uid != os.getuid() or not stat.S_ISREG(st.st_mode)
                or stat.S_IMODE(st.st_mode) & 0o022 or digest(p.read_bytes()) != digest(data)):
            return False
    return all(not (BIN / name).exists() and not (BIN / name).is_symlink() for name in absent)


def service_contract():
    checks = classify(query(), manager=BIN / "bob-activity-manager")
    # The old v0.7.0 pinned SHA deliberately fails after the v0.7.1 upgrade.
    return all(ok for name, ok in checks.items() if name != "pinned_installed_executable")


def check_http(authorization, *, updated=False):
    paths = ["/healthz", "/", "/activity", "/originals"]
    if updated:
        paths += ["/settings", "/system/status", "/api/system/status"]
    for path in paths:
        conn = HTTPConnection("127.0.0.1", 18790, timeout=4)
        try:
            conn.request("GET", path, headers={
                "Host": "127.0.0.1:18790", "Authorization": authorization})
            response = conn.getresponse()
            data = response.read(262145)
            if response.status != 200 or len(data) > 262144:
                return False
            if path == "/healthz":
                if json.loads(data).get("ok") is not True:
                    return False
            elif path == "/api/system/status":
                if not isinstance(json.loads(data).get("services"), list):
                    return False
            elif b"<html" not in data.lower():
                return False
            if updated and path == "/" and b"v0.7.2" not in data:
                return False
            if updated and path == "/settings" and b"Change dashboard password" not in data:
                return False
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        finally:
            conn.close()
    return True


def wait_http(auth, updated):
    for attempt in range(8):
        if service_helper.service_active() and check_http(auth, updated=updated):
            return True
        if attempt != 7:
            time.sleep(0.6)
    return False


def readiness():
    old, new = releases()
    if not installed_matches(old, set(new) - set(old)):
        raise ValueError("live installation differs from approved v0.7.1")
    if not service_contract():
        raise ValueError("unexpected user-systemd service configuration")
    auth = service_helper.authenticate()
    if not service_helper.service_active() or not check_http(auth):
        raise ValueError("existing authenticated dashboard unhealthy")
    if state() is not None:
        raise ValueError("v0.7.2 deployment journal already exists")
    if DB.is_symlink() or not DB.is_file():
        raise ValueError("expected SQLite database unavailable")
    return old, new, auth


def sealed_old(old):
    for name, data in old.items():
        p = STATE / ("before-" + name)
        if p.is_symlink():
            raise ValueError("unsafe private baseline")
        if p.exists():
            if p.read_bytes() != data:
                raise ValueError("baseline archive drift")
        else:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            fsync_dir(STATE)


def roll_back(old, new, auth):
    # Allow only known old/new hashes and expected absent/present modules.
    for name, wanted in new.items():
        target = BIN / name
        if target.is_symlink():
            raise ValueError("installed symlink: manual recovery required")
        if name in old:
            if not target.is_file() or target.read_bytes() not in (old[name], wanted):
                raise ValueError("installed file unexpectedly modified")
        elif target.exists() and (not target.is_file() or target.read_bytes() != wanted):
            raise ValueError("installed added module unexpectedly modified")
    record("rollback_started")
    for name, baseline in old.items():
        target = BIN / name
        if target.read_bytes() != baseline:
            replace_file(target, baseline, digest(new[name]), FILE_MODES[name])
    for name in set(new) - set(old):
        target = BIN / name
        if target.exists():
            target.unlink()
            fsync_dir(BIN)
    record("recovery_requested")
    service_helper.service("restart")
    if not installed_matches(old, set(new) - set(old)) or not wait_http(auth, updated=False):
        record("incident")
        raise RuntimeError("original dashboard recovery failed")
    record("rolled_back")
    return "baseline_restored"


def apply():
    old, new, auth = readiness()
    fd = hold_lock()
    try:
        # Recheck under lock before writing anything.
        if state() is not None or not installed_matches(old, set(new) - set(old)):
            raise ValueError("concurrent upgrade or changed installed files")
        # Online backup is verified before any production code is touched.
        backup = create_verified_backup(DB, BACKUPS)
        sealed_old(old)
        record("prepared")
        try:
            for name in ("bob_dashboard_auth.py", "bob_live_status.py",
                         "navigation_shell.py", "bob-activity-manager"):
                expected = digest(old[name]) if name in old else None
                replace_file(BIN / name, new[name], expected, FILE_MODES[name])
            record("files_installed")
            service_helper.service("restart")
            record("restart_requested")
            if not installed_matches(new, ()) or not wait_http(auth, updated=True):
                raise RuntimeError("upgraded dashboard health failed")
            record("complete")
            return "v0.7.2_installed", backup["backup_path"]
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
            try:
                result = roll_back(old, new, auth)
            except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
                record("incident")
                raise RuntimeError("rollback incident; inspection required") from None
            return result, backup["backup_path"]
    finally:
        os.close(fd)


def recover():
    fd = hold_lock()
    try:
        phase = state()
        if phase is None or phase in ("complete", "rolled_back", "incident"):
            raise ValueError("no recoverable incomplete v0.7.2 transaction")
        old, new = releases()
        for name, data in old.items():
            p = STATE / ("before-" + name)
            if p.is_symlink() or not p.is_file() or p.read_bytes() != data:
                raise ValueError("private recovery source changed")
        return roll_back(old, new, service_helper.authenticate())
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--recover", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("must run as ordinary openclaw user")
    if args.apply:
        if args.confirm != CONFIRM:
            print("v0.7.2 UPDATE: REFUSED; explicit upgrade confirmation required")
            return 1
    elif args.recover:
        if args.confirm != RECOVER:
            print("v0.7.2 RECOVERY: REFUSED; explicit recovery confirmation required")
            return 1
    try:
        if args.apply:
            outcome, backup = apply()
            print("v0.7.2 UPDATE:", outcome)
            print("Private database backup:", backup)
        elif args.recover:
            print("v0.7.2 RECOVERY:", recover())
        else:
            readiness()
            print("v0.7.2 UPDATE READINESS: PASS")
            print("Settings, status and v0.7.2 version label are packaged.")
            print("No production files or services changed.")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        print("v0.7.2 UPDATE: REFUSED", type(exc).__name__)
        print("If apply/recovery was attempted, inspect private transaction journal before any retry.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
