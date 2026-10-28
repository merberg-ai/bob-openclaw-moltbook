#!/usr/bin/env python3
"""Read-only, standard-library-only inventory of a working Bob/OpenClawLab host.

No secrets, configuration values, source contents, database rows, or service
unit bodies are copied. The only write is a private JSON inventory report.
This is NOT an installer, updater, or backup tool.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import stat
import subprocess
import sys


REPORT_VERSION = 1
CODE_SUFFIXES = {"", ".py", ".sh", ".bash"}
SENSITIVE_NAME_PARTS = (
    "secret", "token", "password", "passwd", "credential", "api-key",
    "api_key", "auth", "private", ".env", "backup",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_code_candidate(path: Path) -> bool:
    name = path.name.lower()
    if any(part in name for part in SENSITIVE_NAME_PARTS):
        return False
    return (
        (name == "bobctl" or name.startswith(("bob-", "bob_", "moltbook-")))
        and path.suffix.lower() in CODE_SUFFIXES
    )


def is_unit_candidate(name: str) -> bool:
    return (
        name.startswith(("bob-", "openclaw-"))
        and name.endswith((".service", ".timer"))
    )


def file_fingerprint(path: Path) -> dict:
    """Hash one regular file, refusing symlinks (including final-path races)."""
    base = {"path": str(path)}
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            details = os.fstat(stream.fileno())
            if not stat.S_ISREG(details.st_mode):
                return {**base, "status": "not_regular_file"}
            digest = hashlib.sha256()
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
        return {
            **base,
            "size_bytes": details.st_size,
            "sha256": digest.hexdigest(),
            "mode_octal": oct(stat.S_IMODE(details.st_mode)),
            "mtime_utc": datetime.fromtimestamp(
                details.st_mtime, timezone.utc
            ).isoformat(),
        }
    except (OSError, ValueError) as exc:
        return {**base, "status": "unreadable", "error_type": type(exc).__name__}


def inventory_code(directories: list[Path]) -> list[dict]:
    result = []
    visited = set()
    for folder in directories:
        if str(folder) in visited:
            continue
        visited.add(str(folder))
        if folder.is_symlink() or not folder.is_dir():
            continue
        try:
            for path in sorted(folder.iterdir()):
                if not path.is_symlink() and is_code_candidate(path):
                    result.append(file_fingerprint(path))
        except OSError:
            result.append({"directory": str(folder), "status": "unreadable"})
    return result


def inventory_units(directories: list[Path]) -> tuple[list[dict], list[tuple[str, str]]]:
    result = []
    units = set()
    for folder in directories:
        if folder.is_symlink() or not folder.is_dir():
            continue
        try:
            members = sorted(folder.iterdir())
        except OSError:
            result.append({"directory": str(folder), "status": "unreadable"})
            continue
        for path in members:
            if is_unit_candidate(path.name):
                result.append(file_fingerprint(path))
                scope = "user" if "/systemd/user" in str(folder) else "system"
                units.add((scope, path.name))
            elif path.name.endswith((".service.d", ".timer.d")):
                unit_name = path.name[:-2]
                if not is_unit_candidate(unit_name) or path.is_symlink() or not path.is_dir():
                    continue
                try:
                    for dropin in sorted(path.iterdir()):
                        if dropin.suffix == ".conf":
                            result.append(file_fingerprint(dropin))
                except OSError:
                    result.append({"directory": str(path), "status": "unreadable"})
    return result, sorted(units)


def inventory_unit_states(units: list[tuple[str, str]]) -> list[dict]:
    """Read only LoadState/ActiveState/SubState; never read unit properties/secrets."""
    status = []
    for scope, name in units[:60]:
        cmd = [
            "systemctl", "--user" if scope == "user" else "--system",
            "show", name, "--no-pager",
            "--property=LoadState,ActiveState,SubState",
        ]
        try:
            run = subprocess.run(
                cmd, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=3, check=False,
            )
            if run.returncode != 0:
                status.append({"scope": scope, "unit": name, "status": "unavailable"})
                continue
            allowed = {"LoadState", "ActiveState", "SubState"}
            fields = {}
            for line in run.stdout.splitlines():
                key, sep, value = line.partition("=")
                if sep and key in allowed:
                    fields[key] = value
            status.append({"scope": scope, "unit": name, **fields})
        except (OSError, subprocess.TimeoutExpired):
            status.append({"scope": scope, "unit": name, "status": "unavailable"})
    return status


def inventory_sqlite_schema(database: Path) -> dict:
    """Read schema metadata only, never SELECT from an application table."""
    record = {"path": str(database), "status": "not_found"}
    if database.is_symlink():
        return {**record, "status": "symlink_skipped"}
    if not database.is_file():
        return record
    try:
        # mode=ro protects the live DB against accidental modifications.
        uri = database.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=2)) as conn:
            conn.execute("PRAGMA query_only=ON")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            objects = conn.execute(
                "SELECT type, name FROM sqlite_master "
                "WHERE type IN ('table','view','index','trigger') "
                "AND name NOT LIKE 'sqlite_%' ORDER BY type, name"
            ).fetchall()
            tables = []
            others = []
            for kind, name in objects:
                if kind == "table":
                    escaped = name.replace('"', '""')
                    columns = conn.execute(
                        'PRAGMA table_info("' + escaped + '")'
                    ).fetchall()
                    tables.append({
                        "name": name,
                        "columns": [
                            {"name": row[1], "declared_type": row[2], "pk": bool(row[5])}
                            for row in columns
                        ],
                    })
                else:
                    others.append({"type": kind, "name": name})
            return {
                "path": str(database), "status": "read_only_schema",
                "user_version": version, "tables": tables, "other_objects": others,
            }
    except (OSError, sqlite3.Error, ValueError) as exc:
        return {
            "path": str(database), "status": "unavailable",
            "error_type": type(exc).__name__,
        }


def build_inventory(
    home: Path,
    code_dirs: list[Path],
    unit_dirs: list[Path],
    database: Path,
    include_unit_states: bool = True,
) -> dict:
    code = inventory_code(code_dirs)
    service_files, units = inventory_units(unit_dirs)
    return {
        "report_version": REPORT_VERSION,
        "created_utc": utc_now(),
        "purpose": "local private read-only baseline inventory; NOT a backup",
        "runtime": {
            "python": platform.python_version(),
            "system": platform.system(),
            "kernel_release": platform.release(),
        },
        "scan_roots": {
            "home": str(home),
            "code_dirs": [str(p) for p in code_dirs],
            "unit_dirs": [str(p) for p in unit_dirs],
        },
        "code_files": code,
        "unit_files": service_files,
        "unit_states": inventory_unit_states(units) if include_unit_states else [],
        "sqlite_schema": inventory_sqlite_schema(database),
        "limitations": [
            "No file contents or service environment values collected",
            "Only known script names in specified nonrecursive code directories scanned",
            "Windows startup tasks and source-to-reference diffs require separate checks",
            "SQLite application rows and live database backup not collected",
            "Do not commit this private report to a public repository",
        ],
    }


def write_private_report(data: dict, folder: Path) -> Path:
    # Do not follow an output symlink into an unexpected location.
    if folder.is_symlink():
        raise PermissionError("Output directory must not be a symlink")
    # Do not weaken permissions of any existing directory supplied by the user.
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise PermissionError("Output directory is not private (requires mode 0700)")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = folder / ("inventory-" + stamp + "-" + str(os.getpid()) + ".json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        help="Private report directory; default ~/.local/state/bob-baseline",
    )
    parser.add_argument(
        "--include-code-dir", type=Path, action="append", default=[],
        help="Additional NONRECURSIVE executable directory (repeatable)",
    )
    parser.add_argument(
        "--database", type=Path,
        help="Optional alternate activity-queue.sqlite3 path",
    )
    parser.add_argument(
        "--skip-unit-states", action="store_true",
        help="Skip read-only systemctl show queries",
    )
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as the OpenClawLab operator account, never as root")
    home = Path.home()
    code_dirs = [
        home / ".local/bin", home / "bin",
        home / ".local/share/bob", home / ".local/lib/bob",
        *args.include_code_dir,
    ]
    unit_dirs = [
        home / ".config/systemd/user", Path("/etc/systemd/system"),
        Path("/usr/lib/systemd/user"), Path("/lib/systemd/system"),
    ]
    db = args.database or (home / ".config/moltbook/activity-queue.sqlite3")
    output = args.output_dir or (home / ".local/state/bob-baseline")
    result = build_inventory(
        home, code_dirs, unit_dirs, db,
        include_unit_states=not args.skip_unit_states,
    )
    path = write_private_report(result, output)
    print("Private inventory saved:", path)
    print(
        "Found", len(result["code_files"]), "code candidates,",
        len(result["unit_files"]), "unit files/drop-ins;",
        "SQLite:", result["sqlite_schema"]["status"],
    )
    print("No sources, credentials, database rows, or logs were copied.")
    print("Do not add this JSON report to GitHub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
