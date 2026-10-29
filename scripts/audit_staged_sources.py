#!/usr/bin/env python3
"""Inspect a PRIVATE Bob source snapshot; only print redacted finding locations.

Do not upload the archive. No source lines, detected strings, secret hashes,
host paths, or literal values are printed by this tool.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile
import tokenize

from stage_live_sources import (
    HIGH_RISK_MARKER,
    LITERAL_SECRET,
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_TOTAL_BYTES,
)

MANIFEST = "PRIVATE-SOURCE-MANIFEST.json"
ALLOWED_MEMBER = re.compile(
    r"(?:bin|lib/bob|share/bob)/[A-Za-z0-9_.-]+"
)
MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024


def _read_member(bundle: tarfile.TarFile, member: tarfile.TarInfo, limit: int) -> bytes:
    if not member.isfile() or member.size > limit:
        raise ValueError("Invalid or oversized archive member")
    stream = bundle.extractfile(member)
    if stream is None:
        raise ValueError("Archive member is unreadable")
    with stream:
        result = stream.read(limit + 1)
    if len(result) != member.size or len(result) > limit:
        raise ValueError("Archive member has an invalid length")
    return result


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1



def _syntax_context(source: str, value_start: int, value_end: int) -> str:
    """Classify source location without returning token contents or values.

    Lexical evidence only, not a verdict on whether a credential is genuine.
    """
    line = source.count("\n", 0, value_start) + 1
    last_nl = source.rfind("\n", 0, value_start)
    column = value_start - (last_nl + 1)
    point = (line, column)
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.start <= point < token.end:
                if token.type == tokenize.COMMENT:
                    return "inside Python comment"
                if token.type == tokenize.STRING:
                    lines = source.splitlines(keepends=True)
                    start = sum(len(s) for s in lines[:token.start[0]-1]) + token.start[1]
                    end = sum(len(s) for s in lines[:token.end[0]-1]) + token.end[1]
                    raw = source[start:end]
                    # For a simple quoted literal, value exactly occupies
                    # the token's body. Otherwise it is embedded in a larger
                    # string (perhaps a help message or example).
                    if re.fullmatch(r"(?i:[rubf]{0,3})['\"][^'\"]*['\"]", raw, re.DOTALL):
                        opening = raw.find('"') if '"' in raw else raw.find("'")
                        if (
                            value_start == start + opening + 1
                            and value_end == end - 1
                        ):
                            return "direct Python string literal"
                    return "embedded in Python string text"
                return "Python source expression"
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return "unclassified Python text"
    return "unclassified Python text"

def audit_archive(archive_path: Path) -> dict:
    if archive_path.is_symlink() or not archive_path.is_file():
        raise ValueError("Archive is absent or a symlink")
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive is unexpectedly large")
    findings: list[dict] = []
    total_bytes = 0
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive entries")
        if len(names) < 2 or len(names) > MAX_FILES + 1 or MANIFEST not in names:
            raise ValueError("Missing manifest or invalid member count")
        if any(
            name != MANIFEST and not ALLOWED_MEMBER.fullmatch(name)
            for name in names
        ):
            raise ValueError("Unexpected archive entry")
        manifest_info = archive.getmember(MANIFEST)
        manifest = json.loads(
            _read_member(archive, manifest_info, MAX_MANIFEST_BYTES).decode("utf-8")
        )
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) != len(names) - 1:
            raise ValueError("Manifest/source count mismatch")
        expected_names = {item["archive_path"] for item in entries}
        if expected_names != set(names) - {MANIFEST}:
            raise ValueError("Archive does not match manifest")
        for item in entries:
            filename = item["archive_path"]
            if not ALLOWED_MEMBER.fullmatch(filename):
                raise ValueError("Invalid manifest filename")
            data = _read_member(archive, archive.getmember(filename), MAX_FILE_BYTES)
            total_bytes += len(data)
            if total_bytes > MAX_TOTAL_BYTES:
                raise ValueError("Snapshot exceeds source size limit")
            if (
                hashlib.sha256(data).hexdigest() != item["sha256"]
                or len(data) != item["bytes"]
            ):
                raise ValueError("Snapshot hash mismatch")
            source = data.decode("utf-8")
            for match in LITERAL_SECRET.finditer(source):
                findings.append({
                    "file": filename,
                    "line": _line_number(source, match.start()),
                    "category": "credential-like literal assignment",
                    "syntax_context": _syntax_context(source, match.start("value"), match.end("value")),
                })
            for match in HIGH_RISK_MARKER.finditer(source):
                findings.append({
                    "file": filename,
                    "line": _line_number(source, match.start()),
                    "category": "credential-shaped token or private-key marker",
                    "syntax_context": _syntax_context(source, match.start(), match.end()),
                })
    findings.sort(key=lambda row: (row["file"], row["line"], row["category"]))
    if manifest.get("secret_indicators_total") != len(findings):
        raise ValueError("Audit and staging findings differ")
    return {"files_checked": len(entries), "flag_count": len(findings), "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Explicit private source archive")
    args = parser.parse_args()
    home = Path.home()
    folder = home / ".local/state/bob-baseline/source-staging"
    if args.archive is not None:
        path = args.archive
    else:
        candidates = sorted(folder.glob("bob-source-review-*.tar.gz"))
        if not candidates:
            parser.error("No private source snapshot found")
        path = candidates[-1]
    try:
        result = audit_archive(path)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            json.JSONDecodeError, tarfile.TarError):
        print("Audit FAILED: invalid or unreadable source snapshot; no code disclosed.",
              file=sys.stderr)
        return 1
    print("Source files checked:", result["files_checked"])
    print("Potential secret indicators:", result["flag_count"])
    for finding in result["findings"]:
        print(f'{finding["file"]}:{finding["line"]}: {finding["category"]} ({finding["syntax_context"]})')
    print("Syntax context is only a heuristic, not proof that a credential is harmless.")
    print("No matched strings, source text, or credentials were printed.")
    print("DO NOT publish the raw source archive. Manual review still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
