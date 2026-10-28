#!/usr/bin/env python3
"""Prove source-only update / rollback semantics in an isolated temporary sandbox.

This is NOT a production installer. No process restarts, systemd, Windows, API,
credentials, or live SQLite access. Uses the reviewed nine-file baseline only.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import tempfile

from import_verified_sources import SOURCES

MAX_SOURCE_BYTES = 2 * 1024 * 1024


def source_bytes(source_root: Path) -> dict[str, bytes]:
    expected = set(SOURCES)
    found = set()
    for directory in ("bin", "lib/bob"):
        path = source_root / directory
        if path.is_symlink() or not path.is_dir():
            raise ValueError("Missing or symlinked source directory")
        for file in path.iterdir():
            if not file.is_file() or file.is_symlink():
                raise ValueError("Unexpected source entry")
            found.add(directory + "/" + file.name)
    if found != expected:
        raise ValueError("Source membership does not match reviewed baseline")
    result = {}
    for relative, sha in SOURCES.items():
        file = source_root / relative
        fd = os.open(file, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SOURCE_BYTES:
                raise ValueError("Unexpected source file type or size")
            data = stream.read(MAX_SOURCE_BYTES + 1)
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError("Reviewed source hash mismatch: " + relative)
        compile(data, relative, "exec")
        result[relative] = data
    return result


def stage_release(root: Path, name: str, sources: dict[str, bytes]) -> Path:
    if name not in {"baseline", "candidate"}:
        raise ValueError("Invalid synthetic release label")
    releases = root / "releases"
    dest = releases / name
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("Release exists")
    dest.mkdir(parents=True)
    for relative, data in sources.items():
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if relative.startswith("bin/") else 0o644)
    (dest / "REHEARSAL-MANIFEST.json").write_text(
        json.dumps({"label": name, "source_sha256": {
            relative: hashlib.sha256(data).hexdigest()
            for relative, data in sources.items()
        }}, sort_keys=True), encoding="utf-8"
    )
    return dest


def verify_release(root: Path, name: str) -> None:
    path = root / "releases" / name
    raw = json.loads((path / "REHEARSAL-MANIFEST.json").read_text(encoding="utf-8"))
    if raw.get("label") != name or set(raw.get("source_sha256", {})) != set(SOURCES):
        raise ValueError("Invalid rehearsal manifest")
    for relative, sha in raw["source_sha256"].items():
        source = path / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError("Missing release source file")
        if hashlib.sha256(source.read_bytes()).hexdigest() != sha:
            raise ValueError("Release content was modified")


def swap(root: Path, name: str) -> None:
    if name not in {"baseline", "candidate"}:
        raise ValueError("Unapproved target")
    verify_release(root, name)
    current = root / "current"
    if current.exists() and not current.is_symlink():
        raise ValueError("Refusing to replace an unexpected current path")
    new_link = root / ".incoming-link"
    if new_link.exists() or new_link.is_symlink():
        raise FileExistsError("Stale rehearsal link")
    try:
        new_link.symlink_to(Path("releases") / name, target_is_directory=True)
        os.replace(new_link, current)
    finally:
        if new_link.is_symlink():
            new_link.unlink()


def active(root: Path) -> str:
    link = root / "current"
    if not link.is_symlink():
        raise ValueError("Missing active release link")
    relative = os.readlink(link)
    if relative not in {"releases/baseline", "releases/candidate"}:
        raise ValueError("Unexpected release pointer")
    return relative.split("/")[-1]


def online_backup(database: Path, target: Path) -> None:
    with closing(sqlite3.connect(database)) as source, \
         closing(sqlite3.connect(target)) as backup:
        source.backup(backup)
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Synthetic SQLite backup failed integrity check")


def prove_isolated_rehearsal(source_root: Path, *, report_root: Path | None = None) -> dict:
    sources = source_bytes(source_root)
    # A caller can specify a TEST-owned sandbox for unit tests only; no CLI flag.
    if report_root is None:
        with tempfile.TemporaryDirectory(prefix="bob-v070-rollback-rehearsal-") as scratch:
            return run_rehearsal(Path(scratch), sources)
    return run_rehearsal(report_root, sources)


def run_rehearsal(root: Path, sources: dict[str, bytes]) -> dict:
    if root.exists() and any(root.iterdir()):
        raise ValueError("Rehearsal root must be empty")
    root.mkdir(parents=True, exist_ok=True)
    stage_release(root, "baseline", sources)
    stage_release(root, "candidate", sources)
    verify_release(root, "baseline")
    verify_release(root, "candidate")
    swap(root, "baseline")
    if active(root) != "baseline":
        raise AssertionError("Initial source selection failed")

    database = root / "synthetic-state.sqlite3"
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("CREATE TABLE synthetic_events (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO synthetic_events(value) VALUES ('pre-upgrade')")
        conn.commit()
    online_backup(database, root / "synthetic-backup.sqlite3")

    swap(root, "candidate")
    if active(root) != "candidate":
        raise AssertionError("Synthetic upgrade did not select candidate")
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("INSERT INTO synthetic_events(value) VALUES ('post-upgrade')")
        conn.commit()

    # Reproduce a failed post-swap health gate. Code ONLY is rolled back.
    health_check_passed = False
    if not health_check_passed:
        swap(root, "baseline")
    if active(root) != "baseline":
        raise AssertionError("Failed health gate did not roll back code")
    verify_release(root, active(root))
    with closing(sqlite3.connect(database)) as conn:
        values = [row[0] for row in conn.execute(
            "SELECT value FROM synthetic_events ORDER BY id"
        )]
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise AssertionError("Synthetic live DB integrity failed")
    if values != ["pre-upgrade", "post-upgrade"]:
        raise AssertionError("Rollback lost writes made after backup")
    with closing(sqlite3.connect(root / "synthetic-backup.sqlite3")) as conn:
        backup_values = [row[0] for row in conn.execute(
            "SELECT value FROM synthetic_events ORDER BY id"
        )]
    if backup_values != ["pre-upgrade"]:
        raise AssertionError("Synthetic online backup was not independent")
    return {
        "source_files": len(sources),
        "source_sha256_checked": True,
        "staging_verified": True,
        "atomic_switch_verified": True,
        "failed_health_rollback_verified": True,
        "sqlite_online_backup_verified": True,
        "post_upgrade_writes_preserved": True,
        "live_install_modified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as unprivileged openclaw user")
    root = Path(__file__).resolve().parents[1]
    try:
        results = prove_isolated_rehearsal(root / "src")
    except (OSError, ValueError, AssertionError, RuntimeError, SyntaxError,
            sqlite3.Error, json.JSONDecodeError) as exc:
        print("ISOLATED RELEASE REHEARSAL FAILED:", type(exc).__name__,
              "(production untouched)", file=sys.stderr)
        return 1
    print("ISOLATED RELEASE REHEARSAL: PASS")
    for key, value in results.items():
        print(" ", key + ":", value)
    print("All synthetic release and database files were automatically removed.")
    print("No production code, service units, settings, secrets or live database changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
