"""One signed R4 additive migration inside the existing guarded updater.

No public API, timers, systemd mutations, live DB restore, or new publisher.
Callable ONLY from the existing updater's locked transaction after its exact
source hashes have been installed/registered, one private SQLite backup has
passed independent restore integrity, and R3 publisher-service preflight has
passed. Code rollback deliberately NEVER replaces SQLite after migration.

This file is a trusted part of the Git-reviewed updater checkout, never a
separate owner-facing migration CLI. It is not exposed by the dashboard.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3
import stat

RELEASE="v0.8.0-autonomy1"
FROM="v0.8.0-r3canary1"
REQUIRED=frozenset((
    "bob-release-updater","bobctl","bob-activity-manager",
    "bob-moltbook-publisher","bob_r4_schema.py","bob_r4_outbox.py",
    "bob_r4_suggestions.py","bob_r4_ledger.py",
    "bob_r4_publisher_adapter.py","bob_r4_installed_gate.py",
))
SEND_OFF=(
    ("bob-moltbook-publisher",b"R4_SINGLE_PUBLISHER_COMPILED_OFF = True"),
    ("bob_r4_publisher_adapter.py",b"R4_REAL_DISPATCH_COMPILED_OFF=True"),
    ("bob_r4_publisher_adapter.py",b"R4_EXACT_OWNER_SEND_COMPILED_OFF=True"),
    ("bob_r4_outbox.py",b"PUBLIC_DISPATCH_COMPILED_OFF=True"),
)
MIGRATION_GATE=b"INSTALL_HOOK_COMPILED_OFF=False"
MAX_BACKUP_BYTES=512*1024*1024


def reviewed_scope(current,plan,contents)->bool:
    """Read-only checked release chain and the exact hard-Off payload bytes."""
    try:
        if (not isinstance(current,dict) or not isinstance(plan,dict)
                or current.get("release")!=FROM
                or plan.get("from")!=FROM or plan.get("release")!=RELEASE
                or plan.get("restart_manager") is not True
                or not isinstance(contents,dict)
                or not REQUIRED.issubset(contents)
                or any(type(data) is not bytes for data in contents.values())):
            return False
        for name,marker in SEND_OFF:
            if marker not in contents[name]:
                return False
        return MIGRATION_GATE in contents["bob_r4_schema.py"]
    except (TypeError,KeyError):
        return False


def _private(path:Path,*,directory:bool):
    if path.is_symlink() or not path.exists():
        raise ValueError("r4_migration_private_path_missing")
    info=path.stat()
    if (info.st_uid!=os.geteuid() or
            not (stat.S_ISDIR(info.st_mode) if directory
                 else stat.S_ISREG(info.st_mode)) or
            (stat.S_IMODE(info.st_mode)&0o077)!=0):
        raise ValueError("r4_migration_private_permissions")


def verify_backup_evidence(report,*,backup_dir:Path)->bool:
    """The updater created an online backup and restored it elsewhere.

    Re-hash the exact private artifact before touching production schema.
    Report fields alone do NOT prove a backup exists.
    """
    try:
        if type(report) is not dict or not isinstance(backup_dir,Path):
            return False
        if (report.get("integrity_check")!="ok"
                or report.get("restore_rehearsal")!="passed"
                or type(report.get("sha256")) is not str
                or len(report["sha256"])!=64
                or type(report.get("bytes")) is not int):
            return False
        _private(backup_dir,directory=True)
        path=Path(report["backup_path"])
        if (path.parent.resolve()!=backup_dir.resolve()
                or path.name in (".","..")
                or path.is_symlink()
                or not path.name.startswith("bob-activity-")
                or not path.name.endswith(".sqlite3")):
            return False
        _private(path,directory=False)
        if not 0<path.stat().st_size==report["bytes"]<=MAX_BACKUP_BYTES:
            return False
        sha=hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda:f.read(1024*1024),b""):
                sha.update(block)
        if sha.hexdigest()!=report["sha256"]:
            return False
        with closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)) as db:
            return db.execute("PRAGMA quick_check").fetchall()==[("ok",)]
    except (OSError,KeyError,TypeError,ValueError,sqlite3.Error):
        return False


def run_migration(*,schema_module,db_path:Path,
                  backup,backup_dir:Path,
                  current,plan,contents,
                  candidate_hashes_verified:bool,
                  publisher_inactive:bool)->str:
    """Guarded migration stage called by the updater under its exclusive lock.

    This explicit dependency injection is for offline SQLite tests; the live
    updater must import its hash-verified installed bob_r4_schema.py module.
    Caller attestations are never accepted without the concrete backup and
    code-scope checks here.
    """
    if (not reviewed_scope(current,plan,contents)
            or candidate_hashes_verified is not True
            or publisher_inactive is not True
            or not verify_backup_evidence(backup,backup_dir=backup_dir)):
        raise ValueError("r4_install_release_backup_or_publisher_unverified")
    _private(db_path,directory=False)
    if db_path.is_symlink() or db_path.stat().st_size>MAX_BACKUP_BYTES:
        raise ValueError("r4_install_database_untrusted")
    if not hasattr(schema_module,"migrate_candidate"):
        raise ValueError("r4_install_schema_module_unavailable")
    with closing(sqlite3.connect(db_path,timeout=15,isolation_level=None)) as db:
        if db.execute("PRAGMA quick_check").fetchall()!=[("ok",)]:
            raise ValueError("r4_install_database_integrity_unverified")
        state=schema_module.inspect(db)
        if state not in ("missing","ready"):
            raise ValueError("r4_install_partial_or_future_schema")
        result=schema_module.migrate_candidate(
            db,trusted_owner=True,backup_verified=True,
            installed_release=RELEASE)
        if result!="ready" or schema_module.inspect(db)!="ready":
            raise ValueError("r4_install_schema_postflight_failed")
        if db.execute("PRAGMA quick_check").fetchall()!=[("ok",)]:
            raise ValueError("r4_install_postmigration_integrity")
    return "additive_schema_ready_no_public_send"
