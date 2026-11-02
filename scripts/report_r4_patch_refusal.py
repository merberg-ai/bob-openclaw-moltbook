#!/usr/bin/env python3
"""R4 patch refusal: sanitized READ-ONLY pretransaction diagnostic.

This captures CURRENT pre-archive gates, not the hidden historical ValueError.
No updater invocation, lock acquisition, database backup, SQLite mutation,
service change, OpenClaw call or Moltbook API request. The only HTTP is the
existing authenticated loopback HTTPS Manager health GET.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as u

OLD="v0.8.0-autonomy1"
NEW="v0.8.0-r4propose1"
CHECKS=(
    "signed_current_hashes",
    "completed_prior_journal",
    "private_updater_directory",
    "valid_lock_metadata",
    "publisher_idle_at_snapshot",
    "authenticated_loopback_https",
    "private_sqlite_readable",
    "private_backup_directory",
    "patch_archive_absent",
    "expected_four_file_offer",
)


def _probe(fn):
    try:
        return fn() is True
    except (OSError,ValueError,RuntimeError,TypeError,KeyError,
            AttributeError,sqlite3.Error,PermissionError):
        return False


def _private_directory(p:Path)->bool:
    s=p.lstat()
    return (stat.S_ISDIR(s.st_mode) and s.st_uid==os.geteuid()
            and not p.is_symlink() and
            stat.S_IMODE(s.st_mode)&0o077==0
            and os.access(p,os.R_OK|os.W_OK|os.X_OK))


def _lock_metadata()->bool:
    p=u.LOCK
    if not p.exists() and not p.is_symlink():
        # locked() would create a 0600 file; this script does NOT create one.
        return True
    s=p.lstat()
    return (stat.S_ISREG(s.st_mode) and not p.is_symlink()
            and s.st_uid==os.geteuid() and
            stat.S_IMODE(s.st_mode)&0o077==0)


def _sqlite_ro()->bool:
    p=u.DB
    if p.is_symlink():
        return False
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid():
        return False
    with closing(sqlite3.connect(p.absolute().as_uri()+"?mode=ro",
                                 uri=True,timeout=4)) as db:
        db.execute("PRAGMA query_only=ON")
        return db.execute("SELECT 1").fetchone()==(1,)


def inspect()->dict:
    """No raw errors, secrets, file paths, logs or data/SQL rows in output."""
    checks={name:False for name in CHECKS}
    registry=None
    plan=None
    journal=None
    try:
        registry=u.registry()
    except (OSError,ValueError,TypeError,KeyError):
        pass
    try:
        plan=u.manifest(ROOT)
    except (OSError,ValueError,TypeError,KeyError):
        pass
    try:
        journal=u.read_journal()
    except (OSError,ValueError,TypeError,KeyError):
        pass

    installed=(registry.get("release") if isinstance(registry,dict)
               else "unverified")
    offered=(plan.get("release") if isinstance(plan,dict)
             else "unverified")

    checks["signed_current_hashes"]=(
        installed==OLD and _probe(lambda:u.live_ok(registry)))
    checks["completed_prior_journal"]=(
        isinstance(journal,dict) and
        journal.get("release")==OLD and journal.get("phase")=="complete")
    checks["private_updater_directory"]=_probe(
        lambda:_private_directory(u.STATE_DIR))
    checks["valid_lock_metadata"]=_probe(_lock_metadata)
    checks["publisher_idle_at_snapshot"]=_probe(u.r4_publisher_inactive)
    checks["authenticated_loopback_https"]=(
        installed==OLD and _probe(
            lambda:u.healthy(u.authorization(),release=OLD)))
    checks["private_sqlite_readable"]=_probe(_sqlite_ro)
    checks["private_backup_directory"]=_probe(
        lambda:_private_directory(u.BACKUP_DIR))
    checks["patch_archive_absent"]=not (
        (u.STATE_DIR/("tx-"+NEW)).exists() or
        (u.STATE_DIR/("tx-"+NEW)).is_symlink())
    checks["expected_four_file_offer"]=(
        isinstance(plan,dict) and offered==NEW and
        plan.get("from")==OLD and plan.get("restart_manager") is True and
        isinstance(plan.get("files"),list) and
        {item.get("name") for item in plan["files"]
         if isinstance(item,dict)}==
        {"bob-release-updater","bobctl","bob_r4_agent.py",
         "bob_r4_installed_gate.py"} and len(plan["files"])==4)

    blockers=[key for key in CHECKS if not checks[key]]
    return {
        "format":"r4-prearchive-refusal-snapshot-v1",
        "installed_release":installed,
        "offered_release":offered,
        "checks":checks,
        "current_blockers":blockers,
        "currently_no_observed_prearchive_blocker":not blockers,
        "historical_failure_reason_known":False,
        "patch_installed_by_report":False,
        "host_files_changed_by_report":False,
        "database_changed_by_report":False,
        "services_changed_by_report":False,
        "public_social_requests_by_report":0,
        "retry_authorized_by_report":False,
    }


def main(argv=None)->int:
    args=sys.argv[1:] if argv is None else argv
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r4_patch_refusal.py --check")
        return 2
    data=inspect()
    print(json.dumps(data,sort_keys=True,separators=(",",":")))
    return 0 if not data["current_blockers"] else 1


if __name__=="__main__":
    raise SystemExit(main())
