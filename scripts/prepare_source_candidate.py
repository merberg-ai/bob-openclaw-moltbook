#!/usr/bin/env python3
"""Build a private, pre-reviewed source candidate from the SHA-pinned snapshot.

No publication, installation, service restarts, or live-source modifications.
Only the two known stdout-password disclosures in bob-lan-config are rewritten.
Candidate is for security review; it is NOT automatically safe to publish.
"""

from __future__ import annotations

import argparse
import ast
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
import zipfile

from audit_staged_sources import (
    ALLOWED_MEMBER, MANIFEST, _read_member, audit_archive, MAX_FILE_BYTES
)
from review_staged_sources import review_snapshot
from stage_live_sources import HIGH_RISK_MARKER, LITERAL_SECRET, ensure_private

LAN_SCRIPT = "bin/bob-lan-config"
EXPECTED_LAN_PRINT_LINES = {39, 44}
EXPECTED_LAN_PASSWORD_SHA256 = (
    "4c4ebb2168d9e38eaf7156483ed6db7dde0fb377966b945e9b0413556fe76e9b"
)
KNOWN_STATIC_WARNING = ("bin/bobctl", 453, "possible credential-related stdout")
MAX_ARCHIVE_BYTES = 25 * 1024 * 1024


def password_print_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name) or node.func.id != "print":
        return False
    return any(
        isinstance(child, ast.Subscript)
        and isinstance(child.slice, ast.Constant)
        and child.slice.value == "password"
        for arg in node.args for child in ast.walk(arg)
    )


def mask_lan_password_stdout(source: str) -> tuple[str, list[int]]:
    tree = ast.parse(source)
    to_replace: list[int] = []
    for statement in ast.walk(tree):
        if (isinstance(statement, ast.Expr)
                and password_print_call(statement.value)):
            if statement.lineno != statement.end_lineno:
                raise ValueError("Password output spans multiple lines; refuse blind edit")
            to_replace.append(statement.lineno)
    if set(to_replace) != EXPECTED_LAN_PRINT_LINES or len(to_replace) != 2:
        raise ValueError("Expected password print statements differ; manual review required")
    lines = source.splitlines(keepends=True)
    for n in to_replace:
        current = lines[n - 1]
        text = current.rstrip("\r\n")
        newline = current[len(text):]
        stmt = next(
            s for s in ast.walk(tree)
            if isinstance(s, ast.Expr) and s.lineno == n
            and password_print_call(s.value)
        )
        if text.strip() != ast.get_source_segment(source, stmt):
            raise ValueError("Password line includes extra statements or comments")
        indent = text[:len(text) - len(text.lstrip())]
        lines[n - 1] = indent + "print('LAN password: [masked]')" + newline
    result = "".join(lines)
    if len(result.splitlines()) != len(source.splitlines()):
        raise RuntimeError("Sanitization unexpectedly changed line count")
    if any(password_print_call(node) for node in ast.walk(ast.parse(result))):
        raise RuntimeError("Password-print operation remains after masking")
    return result, sorted(to_replace)


def _write_zip_member(zf: zipfile.ZipFile, name: str, data: bytes, executable: bool) -> None:
    info = zipfile.ZipInfo(name)
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.create_system = 3
    info.external_attr = ((stat.S_IFREG | (0o700 if executable else 0o600)) << 16)
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)


def build_candidate(archive: Path, destination: Path) -> dict:
    verified = audit_archive(archive)
    result = review_snapshot(archive)
    if result["files_checked"] != 9 or verified["files_checked"] != 9:
        raise ValueError("Unexpected source inventory size; manual review needed")
    if result["language_counts"] != {"python": 9}:
        raise ValueError("Non-Python source in known baseline; manual review needed")
    if result["possible_nonstdlib_imports"]:
        raise ValueError("External dependencies detected; review before exporting")
    allowed = {
        (LAN_SCRIPT, 39, "possible credential-related stdout"),
        (LAN_SCRIPT, 44, "possible credential-related stdout"),
        KNOWN_STATIC_WARNING
    }
    for finding in result["findings"]:
        signature = (finding["file"], finding["line"], finding["category"])
        if signature not in allowed:
            raise ValueError("Unexpected source-review finding; manual review required")
    if len(result["findings"]) != 3:
        raise ValueError("Source-review baseline has changed")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Refusing to overwrite an existing candidate archive")
    if not destination.parent.is_dir():
        raise FileNotFoundError("Destination directory must already exist")
    if destination.parent.resolve() == archive.parent.resolve():
        raise ValueError("Export to a distinct destination, not source-staging")
    if destination.suffix.lower() != ".zip":
        raise ValueError("Candidate filename must end with .zip")

    modified: list[str] = []
    records = []
    parts = []
    with tarfile.open(archive, "r:gz") as bundle:
        for item in bundle.getmembers():
            name = item.name
            if name == MANIFEST:
                continue
            if not ALLOWED_MEMBER.fullmatch(name):
                raise ValueError("Invalid source path")
            original = _read_member(bundle, item, MAX_FILE_BYTES)
            data = original
            if name == LAN_SCRIPT:
                if hashlib.sha256(original).hexdigest() != EXPECTED_LAN_PASSWORD_SHA256:
                    raise ValueError("LAN helper differs from reviewed baseline; manual review needed")
                rendered, changed_lines = mask_lan_password_stdout(original.decode("utf-8"))
                data = rendered.encode("utf-8")
                if changed_lines != [39, 44]:
                    raise RuntimeError("Unexpected LAN sanitizer change")
                modified.append(name)
            text = data.decode("utf-8")
            if HIGH_RISK_MARKER.search(text) or LITERAL_SECRET.search(text):
                raise ValueError("Potential sensitive literal in candidate; manual review")
            parts.append((name, data))
            records.append({
                "path": name,
                "original_sha256": hashlib.sha256(original).hexdigest(),
                "candidate_sha256": hashlib.sha256(data).hexdigest(),
                "source_modified": name in modified,
            })
    if modified != [LAN_SCRIPT]:
        raise RuntimeError("Password masking was not applied")

    manifest = {
        "purpose": "private reviewed-copy candidate; NOT APPROVED FOR GITHUB",
        "source_count": verified["files_checked"],
        "changed_file": LAN_SCRIPT,
        "changed_lines": sorted(EXPECTED_LAN_PRINT_LINES),
        "notes": [
            "Only the two known runtime password print calls were masked.",
            "CLI bootstrap/retrieval behavior still needs regression validation.",
            "Static scanners cannot prove that source has no secrets or private data.",
            "No systemd unit files, credentials files, state databases or logs included.",
            "Manual review is required before committing code to any public repository.",
        ],
        "sources": sorted(records, key=lambda d: d["path"]),
    }
    payload = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")
    old_mask = os.umask(0o077)
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                with zipfile.ZipFile(stream, "w") as zf:
                    for name, data in parts:
                        _write_zip_member(zf, name, data, name.startswith("bin/"))
                    _write_zip_member(zf, "REVIEW-MANIFEST.json", payload, False)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    finally:
        os.umask(old_mask)
    return {"path": str(destination), "source_count": len(parts), "masked_lines": [39, 44]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Private staged source tarball")
    parser.add_argument("--destination", type=Path, help="Export candidate ZIP path")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as OpenClawLab operator, never root")
    home = Path.home()
    source_dir = home / ".local/state/bob-baseline/source-staging"
    archives = sorted(source_dir.glob("bob-source-review-*.tar.gz"))
    if not archives and args.archive is None:
        parser.error("No staged private source archive found")
    archive = args.archive or archives[-1]
    private_folder = home / ".local/state/bob-baseline/review-candidates"
    if args.destination:
        destination = args.destination
    else:
        ensure_private(private_folder)
        date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destination = private_folder / f"bob-source-candidate-{date}.zip"
    try:
        report = build_candidate(archive, destination)
    except (OSError, ValueError, RuntimeError, SyntaxError, UnicodeError,
            tarfile.TarError, zipfile.BadZipFile) as exc:
        print("SOURCE CANDIDATE FAILED:", type(exc).__name__,
              "(no live code was modified)", file=sys.stderr)
        return 1
    print("Review ZIP created:", report["path"])
    print("Source files:", report["source_count"])
    print("Password output masked in COPY only: bin/bob-lan-config lines 39, 44")
    print("No deploy, no GitHub upload, no live-file changes.")
    print("Candidate is NOT security-approved. Review before sharing or publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
