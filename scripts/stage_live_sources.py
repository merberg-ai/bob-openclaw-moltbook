#!/usr/bin/env python3
"""Stage exact installed Bob source privately, without publishing or deploying.

Reads the prior private inventory, verifies every live file against its SHA-256,
and copies only the inventoried Bob source scripts into a private tar.gz.
No credentials, configs, systemd units, databases or logs are deliberately added.
A heuristic secret scan is informational, NOT a guarantee the sources are safe
to share. NEVER upload the resulting archive until manually reviewed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile

from inventory_live_host import is_code_candidate

MAX_FILES = 100
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024
LITERAL_SECRET = re.compile(
    r"\b(?:api[_-]?key|password|passwd|secret|token|authorization)"
    r"\b\s*[:=]\s*(?P<quote>['\"])(?P<value>[^'\"\r\n]{8,})(?P=quote)",
    re.IGNORECASE,
)
HIGH_RISK_MARKER = re.compile(
    r"gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)


def ensure_private(folder: Path) -> None:
    if folder.is_symlink():
        raise PermissionError("Output directory is symlinked")
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not folder.is_dir() or stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise PermissionError("Output directory must have private permissions (0700)")


def allowed_paths(home: Path) -> dict[Path, str]:
    return {
        home / ".local/bin": "bin",
        home / ".local/lib/bob": "lib/bob",
        home / ".local/share/bob": "share/bob",
    }


def validated_source(path_string: str, home: Path) -> tuple[Path, str]:
    source = Path(path_string)
    roots = allowed_paths(home)
    if not source.is_absolute() or source.parent not in roots:
        raise ValueError("Inventory source path outside approved Bob code directories")
    if (
        source.is_symlink()
        or not source.is_file()
        or not stat.S_ISREG(source.stat().st_mode)
    ):
        raise ValueError("Inventory source missing, symlinked or not a regular file")
    if not is_code_candidate(source):
        raise ValueError("Inventory includes unapproved source filename")
    # Refuse parent-directory symlinks and paths that escape the operator's home.
    if not source.resolve().is_relative_to(home.resolve()):
        raise ValueError("Source resolves outside operator's home")
    for current in (source.parent, source.parent.parent):
        if current.is_symlink():
            raise ValueError("Source directory is symlinked")
    return source, roots[source.parent] + "/" + source.name


def secure_read(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Source is not a regular file")
        if before.st_size > MAX_FILE_BYTES:
            raise ValueError("Source exceeds maximum expected size")
        data = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("Source too large")
        if (
            before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or len(data) != before.st_size
        ):
            raise RuntimeError("Source changed during read; rerun inventory")
        return data


def secret_indicators(data: bytes) -> int:
    if b"\0" in data:
        raise ValueError("Source looks binary, not text")
    text = data.decode("utf-8")  # Fail rather than smuggle opaque bytes.
    return len(LITERAL_SECRET.findall(text)) + len(HIGH_RISK_MARKER.findall(text))


def add_entry(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o600
    info.mtime = 0
    tar.addfile(info, io.BytesIO(data))


def stage_sources(inventory: Path, home: Path, output_dir: Path) -> dict:
    if inventory.is_symlink() or not inventory.is_file():
        raise ValueError("Missing or symlinked private inventory report")
    # Do not read an arbitrary gigantic report.
    if inventory.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("Inventory report is unexpectedly large")
    report = json.loads(inventory.read_text(encoding="utf-8"))
    if report.get("report_version") != 1:
        raise ValueError("Unsupported inventory version")
    files = report.get("code_files")
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("Invalid or empty inventory code file list")
    originals = []
    names = set()
    total = 0
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("Invalid inventory entry")
        expected = entry.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Inventory entry has no valid SHA-256")
        path, archive_name = validated_source(entry.get("path", ""), home)
        if archive_name in names:
            raise ValueError("Duplicate inventory source")
        names.add(archive_name)
        data = secure_read(path)
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise RuntimeError("Installed source differs from prior inventory: " + path.name)
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Source bundle exceeds limit")
        indicators = secret_indicators(data)
        originals.append((
            archive_name, data, {
                "archive_path": archive_name, "live_path": str(path),
                "sha256": actual, "bytes": len(data),
                "secret_indicator_count": indicators,
            }
        ))

    ensure_private(output_dir)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = output_dir / f"bob-source-review-{timestamp}-{os.getpid()}.tar.gz"
    metadata = {
        "purpose": "private, unreviewed exact-source escrow; NOT deployable",
        "inventory_created_utc": report.get("created_utc"),
        "files": [row[2] for row in originals],
        "total_bytes": total,
        "secret_indicators_total": sum(row[2]["secret_indicator_count"] for row in originals),
        "warning": (
            "Automated scanning cannot prove sources are free of secrets. "
            "Never publish this archive; inspect and sanitize before import."
        ),
    }
    old_umask = os.umask(0o077)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                with tarfile.open(fileobj=stream, mode="w:gz") as bundle:
                    for name, data, _ in originals:
                        add_entry(bundle, name, data)
                    add_entry(
                        bundle, "PRIVATE-SOURCE-MANIFEST.json",
                        json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8")
                    )
        except BaseException:
            target.unlink(missing_ok=True)
            raise
    finally:
        os.umask(old_umask)
    return {
        "path": str(target), "files": len(originals), "total_bytes": total,
        "secret_indicators": metadata["secret_indicators_total"],
        "needs_manual_review": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, help="Specific private JSON report")
    parser.add_argument("--output-dir", type=Path, help="Private source staging directory")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as the OpenClawLab operator, not root")
    home = Path.home()
    report_dir = home / ".local/state/bob-baseline"
    if args.inventory:
        inventory = args.inventory
    else:
        candidates = sorted(report_dir.glob("inventory-*.json"))
        if not candidates:
            parser.error("No private inventory found; run inventory_live_host.py first")
        inventory = candidates[-1]
    out = args.output_dir or report_dir / "source-staging"
    try:
        result = stage_sources(inventory, home, out)
    except (OSError, ValueError, RuntimeError, UnicodeError, json.JSONDecodeError) as exc:
        print("Source staging FAILED:", type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print("Private source snapshot:", result["path"])
    print("Files:", result["files"], "source bytes:", result["total_bytes"])
    print("Potential hard-coded secret indicators:", result["secret_indicators"])
    print("MANUAL REVIEW REQUIRED. Never upload or commit this raw archive.")
    print("Live sources, services and SQLite were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
