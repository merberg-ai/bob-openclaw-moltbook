#!/usr/bin/env python3
"""Guarded v0.7.2 live-status refresh update. Production unchanged by default.

Pins currently-installed styled v0.7.2 manager and read-only status module.
Changes only three code files, backed up to a private fsynced journal.
A failed health check rolls back code, never credential or SQLite state.
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

import build_v072_settings_candidate as current
import build_v072_live_candidate as next_release
import deploy_v071_activity_manager as service
from backup_live_sqlite import create_verified_backup
from rehearse_v071_regular_file_installer import replace_file, fsync_dir

HOME = Path.home()
BIN = HOME / ".local/bin"
STATE = HOME / ".local/state/bob-v072-live-status"
JOURNAL = STATE / "transaction.json"
LOCK = STATE / "transaction.lock"
DB = HOME / ".config/moltbook/activity-queue.sqlite3"
BACKUPS = HOME / ".local/state/bob-baseline/backups"
APPROVE = "UPGRADE-BOB-LIVE-STATUS"
RECOVER = "RECOVER-BOB-LIVE-STATUS"
FORMAT = "bob-v072-live-status-v1"
NAMES = ("bob_live_status.py", "bob_status_view.py", "bob-activity-manager")
OLD = Path(__file__).resolve().parents[1] / "release_baselines/v072/bob_live_status.py"
SOURCE = Path(__file__).resolve().parents[1] / "src/lib/bob"


def digest(data):
    return current.prior.sha256(data)


def releases():
    original, old_nav = current.build(styled=True)
    replacement, new_nav = next_release.build()
    if old_nav != new_nav:
        raise ValueError("unexpected navigation change")
    if OLD.is_symlink() or not OLD.is_file():
        raise ValueError("missing pinned old status")
    old_status = OLD.read_bytes()
    compile(old_status, "pinned-status", "exec")
    new_status_path = SOURCE / "bob_live_status.py"
    view_path = SOURCE / "bob_status_view.py"
    for path in (new_status_path, view_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing safe source")
    updated_status = new_status_path.read_bytes()
    updated_view = view_path.read_bytes()
    compile(updated_status, "status", "exec")
    compile(updated_view, "view", "exec")
    if original == replacement or old_status == updated_status:
        raise ValueError("no meaningful status update")
    baseline = {"bob-activity-manager": original, "bob_live_status.py": old_status}
    candidate = {"bob-activity-manager": replacement,
                 "bob_live_status.py": updated_status, "bob_status_view.py": updated_view}
    return baseline, candidate


def safe_state():
    if STATE.is_symlink():
        raise ValueError("symlink deployment state")
    STATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    s = STATE.stat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o077:
        raise ValueError("unprivate deployment state")


def phase():
    if JOURNAL.is_symlink():
        raise ValueError("symlink journal")
    if not JOURNAL.exists():
        return None
    if not JOURNAL.is_file() or JOURNAL.stat().st_size > 512:
        raise ValueError("unexpected journal")
    value = json.loads(JOURNAL.read_text())
    if set(value) != {"format", "phase"} or value["format"] != FORMAT or value["phase"] not in (
            "prepared", "installed", "restarted", "rolling_back",
            "complete", "rolled_back", "incident"):
        raise ValueError("invalid journal")
    return value["phase"]


def journal(next_phase):
    dest = STATE / ".journal-next"
    if dest.exists() or dest.is_symlink():
        raise ValueError("stale pending journal")
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(json.dumps({"format": FORMAT, "phase": next_phase},
                                sort_keys=True).encode())
        output.flush()
        os.fsync(output.fileno())
    os.replace(dest, JOURNAL)
    fsync_dir(STATE)


def locked():
    safe_state()
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    s = os.fstat(fd)
    if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o077:
        os.close(fd)
        raise ValueError("unsafe update lock")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def match_installed(baseline, candidate, upgraded):
    expected = candidate if upgraded else baseline
    for name, data in expected.items():
        path = BIN / name
        if path.is_symlink() or not path.is_file():
            return False
        s = path.stat()
        if s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o022:
            return False
        if digest(path.read_bytes()) != digest(data):
            return False
    if not upgraded and ((BIN / "bob_status_view.py").exists()
                         or (BIN / "bob_status_view.py").is_symlink()):
        return False
    return True


def http_ok(auth, upgraded):
    routes = ("/", "/settings", "/system/status", "/api/system/status")
    for route in routes:
        conn = HTTPConnection("127.0.0.1", 18790, timeout=18 if "status" in route else 4)
        try:
            conn.request("GET", route, headers={
                "Host": "127.0.0.1:18790", "Authorization": auth})
            response = conn.getresponse()
            payload = response.read(262145)
            if response.status != 200 or len(payload) > 262144:
                return False
            if route == "/" and b"v0.7.2" not in payload:
                return False
            if route == "/settings" and b"bob-settings-form" not in payload:
                return False
            if route == "/system/status":
                expected = b"/assets/bob-status.js" if upgraded else b"Recent recorded jobs"
                if expected not in payload:
                    return False
            if route == "/api/system/status":
                if not isinstance(json.loads(payload).get("services"), list):
                    return False
        except (OSError, ValueError, json.JSONDecodeError, TimeoutError):
            return False
        finally:
            conn.close()
    if upgraded:
        conn = HTTPConnection("127.0.0.1", 18790, timeout=4)
        try:
            conn.request("GET", "/assets/bob-status.js", headers={
                "Host": "127.0.0.1:18790", "Authorization": auth})
            response = conn.getresponse()
            if response.status != 200 or b"credentials: 'same-origin'" not in response.read(65536):
                return False
        except OSError:
            return False
        finally:
            conn.close()
    return True


def healthy(auth, upgraded):
    for attempt in range(6):
        if service.service_active() and http_ok(auth, upgraded):
            return True
        if attempt < 5:
            time.sleep(0.7)
    return False


def archive(baseline):
    for name, data in baseline.items():
        target = STATE / ("before-" + name)
        if target.exists() or target.is_symlink():
            raise ValueError("existing archived baseline")
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    fsync_dir(STATE)


def rollback(baseline, candidate, auth):
    # An interrupted operation may have switched any subset of the files.
    for name, updated in candidate.items():
        target = BIN / name
        if target.is_symlink():
            raise ValueError("unexpected symlink during rollback")
        if name in baseline:
            if not target.is_file() or target.read_bytes() not in (baseline[name], updated):
                raise ValueError("externally modified installed code")
        elif target.exists() and (not target.is_file() or target.read_bytes() != updated):
            raise ValueError("unexpected extra module content")
    journal("rolling_back")
    # Restore manager first, so any restart loads original import behavior.
    for name in ("bob-activity-manager", "bob_live_status.py"):
        target = BIN / name
        original = baseline[name]
        if target.read_bytes() != original:
            replace_file(target, original, digest(candidate[name]),
                         0o700 if name == "bob-activity-manager" else 0o600)
    view = BIN / "bob_status_view.py"
    if view.exists():
        view.unlink()
        fsync_dir(BIN)
    try:
        service.service("restart")
        if not match_installed(baseline, candidate, False) or not healthy(auth, False):
            raise RuntimeError("baseline service recovery failed")
        journal("rolled_back")
        return "baseline_restored"
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        journal("incident")
        raise


def apply():
    baseline, candidate = releases()
    fd = locked()
    try:
        if phase() is not None:
            raise ValueError("existing status update journal")
        if not match_installed(baseline, candidate, False):
            raise ValueError("installed dashboard differs from reviewed styled v0.7.2")
        auth = service.authenticate()
        if not healthy(auth, False):
            raise ValueError("existing dashboard health refused")
        # Preserve SQLite state before code changes. Backup never overwrites DB.
        create_verified_backup(DB, BACKUPS)
        archive(baseline)
        journal("prepared")
        try:
            for name in NAMES:
                replace_file(BIN / name, candidate[name],
                             digest(baseline[name]) if name in baseline else None,
                             0o700 if name == "bob-activity-manager" else 0o600)
            journal("installed")
            service.service("restart")
            journal("restarted")
            if not match_installed(baseline, candidate, True) or not healthy(auth, True):
                raise RuntimeError("new status UI health refused")
            journal("complete")
            return "status_ui_updated"
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            try:
                rollback(baseline, candidate, auth)
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
                journal("incident")
                raise RuntimeError("code rollback requires inspection") from None
            return "rolled_back"
    finally:
        os.close(fd)


def recover():
    baseline, candidate = releases()
    fd = locked()
    try:
        stage = phase()
        if stage is None or stage in ("complete", "rolled_back", "incident"):
            raise ValueError("no recoverable interrupted transaction")
        for name, data in baseline.items():
            archived = STATE / ("before-" + name)
            if archived.is_symlink() or not archived.is_file() or archived.read_bytes() != data:
                raise ValueError("sealed original code changed")
        return rollback(baseline, candidate, service.authenticate())
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
        parser.error("non-root user only")
    try:
        if not args.apply and not args.recover:
            baseline, candidate = releases()
            ok = match_installed(baseline, candidate, False)
            print("v0.7.2 LIVE STATUS READINESS:", "PASS" if ok else "REFUSED")
            print("production_modified: NO")
            return 0 if ok else 1
        expected = RECOVER if args.recover else APPROVE
        if args.confirm != expected:
            raise ValueError("explicit confirmation required")
        result = recover() if args.recover else apply()
        print("v0.7.2 LIVE STATUS:", result)
        return 0 if result == "status_ui_updated" or result == "baseline_restored" else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        print("v0.7.2 LIVE STATUS: REFUSED", type(exc).__name__)
        print("Inspect private status journal before retrying an interrupted update.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
