#!/usr/bin/env python3
"""Create and restore-test a private, consistent SQLite online backup.

NO application state changes, no service restarts, no external API calls.
Uses Python stdlib only; NEVER upload resulting database to GitHub.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile


def private_folder(folder: Path) -> None:
    if folder.is_symlink():
        raise PermissionError("backup directory must not be a symlink")
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    mode = folder.stat().st_mode
    if not stat.S_ISDIR(mode) or stat.S_IMODE(mode) & 0o077:
        raise PermissionError("backup directory must be private (mode 0700)")


def schema_digest(conn: sqlite3.Connection) -> str:
    # Check signatures without outputting potentially sensitive DDL defaults.
    rows = conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "ORDER BY type, name, tbl_name"
    ).fetchall()
    h = hashlib.sha256()
    for row in rows:
        for value in row:
            piece = "" if value is None else str(value)
            h.update(len(piece.encode("utf-8")).to_bytes(8, "big"))
            h.update(piece.encode("utf-8"))
    return h.hexdigest()


def check_integrity(conn: sqlite3.Connection) -> None:
    outcome = conn.execute("PRAGMA integrity_check").fetchall()
    if outcome != [("ok",)]:
        raise RuntimeError("backup integrity check failed")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_verified_backup(source: Path, folder: Path) -> dict:
    """Back up live source via SQLite API and rehearse a restore to a temp DB."""
    if source.is_symlink() or not source.is_file():
        raise FileNotFoundError("source SQLite database missing or symlinked")
    if not stat.S_ISREG(source.stat().st_mode):
        raise ValueError("SQLite source is not a regular file")
    private_folder(folder)
    if folder.resolve() == source.parent.resolve():
        raise ValueError("backup folder must differ from live database folder")

    old_mask = os.umask(0o077)
    staging_path = None
    restore_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".backup-pending-", suffix=".sqlite3", dir=folder,
            delete=False
        ) as fp:
            staging_path = Path(fp.name)
        with tempfile.NamedTemporaryFile(
            prefix=".restore-check-", suffix=".sqlite3", dir=folder,
            delete=False
        ) as fp:
            restore_path = Path(fp.name)

        # Query-only source connection; online backup obtains a coherent snapshot.
        src_uri = source.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(src_uri, uri=True, timeout=10)) as src:
            src.execute("PRAGMA query_only=ON")
            with closing(sqlite3.connect(staging_path, timeout=10)) as dst:
                src.backup(dst, pages=128, sleep=0.05)
                check_integrity(dst)
                expected_schema = schema_digest(dst)
                table_count = dst.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                ).fetchone()[0]
                user_version = dst.execute("PRAGMA user_version").fetchone()[0]

        # Restore to an isolated temporary DB, never the production source.
        with closing(sqlite3.connect(staging_path)) as back:
            with closing(sqlite3.connect(restore_path)) as restored:
                back.backup(restored, pages=128, sleep=0.05)
                check_integrity(restored)
                if schema_digest(restored) != expected_schema:
                    raise RuntimeError("restored schema does not match the backup")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        final = folder / f"bob-activity-{timestamp}-{os.getpid()}.sqlite3"
        if final.exists() or final.is_symlink():
            raise FileExistsError("backup filename already exists")
        digest = sha256_file(staging_path)
        size = staging_path.stat().st_size
        # Atomic no-clobber publication on the same filesystem.
        os.link(staging_path, final, follow_symlinks=False)
        return {
            "backup_path": str(final), "bytes": size, "sha256": digest,
            "tables": table_count, "user_version": user_version,
            "integrity_check": "ok", "restore_rehearsal": "passed",
        }
    finally:
        for temp in (staging_path, restore_path):
            if temp is not None:
                temp.unlink(missing_ok=True)
        os.umask(old_mask)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, help="Override live DB path")
    parser.add_argument("--output-dir", type=Path, help="Override private backup folder")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("must run as the OpenClawLab operator user, not root")
    home = Path.home()
    database = args.database or home / ".config/moltbook/activity-queue.sqlite3"
    folder = args.output_dir or home / ".local/state/bob-baseline/backups"
    try:
        report = create_verified_backup(database, folder)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(
            f"Backup FAILED ({type(exc).__name__}). Live database was not replaced.",
            file=sys.stderr,
        )
        return 1
    print("Private verified SQLite backup:", report["backup_path"])
    print("Size:", report["bytes"], "bytes; SHA-256:", report["sha256"])
    print("Tables:", report["tables"], "user_version:", report["user_version"])
    print("Integrity:", report["integrity_check"],
          "isolated restore:", report["restore_rehearsal"])
    print("Never publish/upload/share this backup: it contains private activity records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
