#!/usr/bin/env python3
"""Read-only independent review of a private, non-deployable service candidate ZIP.

Verifies private topology hashes, exact archive membership, and a minimal
allowlist of exported template content. Does not install, contact or alter
services. PASS is a defense-in-depth check, NOT proof of absence of secrets.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

from inventory_service_topology import EXPECTED_NAMES
from prepare_service_template_candidates import (
    BOOL_KEYS, BOOL_VALUES, CALENDAR_RE, CALENDAR_WORDS,
    DEPENDENCIES, DEPENDENCY_KEYS, DURATION_KEYS, DURATION_RE,
    RESTART_TYPES, SAFE_TIMER_KEYS, SENSITIVE_KEYS, SERVICE_TYPES, SAFE_PASSTHROUGH,
)
from report_service_readiness import read_private_report

MAX_ARCHIVE = 2 * 1024 * 1024
MAX_MEMBER = 64 * 1024
MANIFEST = "REVIEW-ONLY-MANIFEST.json"
META_KEYS = {"format","version","deployable","source_count","unit_templates","warnings"}
ITEM_KEYS = {"scope","unit","kind","template","raw_unit_sha256",
             "safe_directive_keys","withheld_known_keys","unclassified_directives_count"}
WARNINGS = [
    "NOT DEPLOYABLE; must be manually reviewed and reconstructed",
    "All Exec and Environment values omitted; no original unit bodies included",
    "Keep output private until every member is reviewed before sharing",
]
HEADER = {
    "# NOT DEPLOYABLE - REVIEW CANDIDATE ONLY",
    "# Original Exec*, Environment*, paths and credentials were NOT copied.",
    "# Generated from hash-verified installed configuration.",
    "# To become deployable: reconstruct and independently review exact behavior.",
    "# WITHHELD KNOWN DIRECTIVES (key names only):",
}
HIDDEN = SENSITIVE_KEYS | DEPENDENCY_KEYS | SAFE_TIMER_KEYS | BOOL_KEYS | SAFE_PASSTHROUGH | {"RestartSec"}


def valid_value(section: str, key: str, value: str) -> bool:
    if (not value or len(value) > 200
            or any(x in value for x in ["\\","$",";",chr(96),"'",'"',"{","}","\t","\r","\n"])):
        return False
    if key in DEPENDENCY_KEYS:
        words = value.split()
        return 0 < len(words) <= 20 and all(w in DEPENDENCIES for w in words)
    if section == "Timer" and key == "OnCalendar":
        return bool(CALENDAR_RE.fullmatch(value)) and all(
            w in CALENDAR_WORDS for w in re.findall(r"[A-Za-z]+", value))
    if section == "Timer" and key in DURATION_KEYS:
        return bool(DURATION_RE.fullmatch(value))
    if section == "Timer" and key == "Unit":
        return value in EXPECTED_NAMES
    if key in BOOL_KEYS:
        return value in BOOL_VALUES
    if section == "Service":
        if key == "Type":
            return value in SERVICE_TYPES
        if key == "Restart":
            return value in RESTART_TYPES
        if key == "RestartSec":
            return bool(DURATION_RE.fullmatch(value))
        if key == "ProtectSystem":
            return value in {"yes","no","full","strict"}
        if key == "ExecStart":
            return value == "@REVIEW_REQUIRED_NOT_DEPLOYABLE@"
    return False


def audit_template(data: bytes, item: dict) -> None:
    text = data.decode("utf-8")
    if len(data) > MAX_MEMBER or "\0" in text or not text.startswith(
            "# NOT DEPLOYABLE - REVIEW CANDIDATE ONLY\n"):
        raise ValueError("Invalid review template")
    comments = set()
    hidden = {}
    other = None
    section = None
    keys = set()
    placeholders = 0
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith("#"):
            if line in HEADER or line in {
                "# Scope: " + item["scope"],
                "# Unit: " + item["unit"],
                "# Kind: " + item["kind"],
            }:
                comments.add(line)
                continue
            match = re.fullmatch(r"# ([A-Za-z][A-Za-z0-9]{0,79}): ([1-9][0-9]{0,5})", line)
            if match and match.group(1) in HIDDEN and match.group(1) not in hidden:
                hidden[match.group(1)] = int(match.group(2))
                continue
            match = re.fullmatch(r"# OTHER UNCLASSIFIED DIRECTIVES: (0|[1-9][0-9]{0,5})", line)
            if match and other is None:
                other = int(match.group(1))
                continue
            raise ValueError("Unexpected template comment")
        if line in {"[Unit]","[Service]","[Timer]","[Install]"}:
            section = line[1:-1]
            continue
        key, sep, value = line.partition("=")
        if (section is None or not sep or not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9]{0,79}", key)
                or not valid_value(section, key, value)):
            raise ValueError("Unapproved directive in template")
        if key == "ExecStart":
            placeholders += 1
        else:
            keys.add(key)
    expected_header = HEADER | {
        "# Scope: " + item["scope"], "# Unit: " + item["unit"], "# Kind: " + item["kind"],
    }
    if (not expected_header.issubset(comments)
            or placeholders != (1 if item["unit"].endswith(".service") else 0)
            or hidden != item["withheld_known_keys"]
            or other != item["unclassified_directives_count"]
            or sorted(keys) != item["safe_directive_keys"]):
        raise ValueError("Template and manifest do not match")


def audit(archive: Path, topology: Path) -> int:
    report = read_private_report(topology)
    if archive.is_symlink():
        raise ValueError("Archive is a symlink")
    fd = os.open(archive, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) & 0o077
                or not 0 < info.st_size <= MAX_ARCHIVE):
            raise ValueError("Archive is not private regular file")
        with zipfile.ZipFile(stream) as z:
            members = z.infolist()
            names = [m.filename for m in members]
            if len(names) != len(set(names)) or len(names) > 121:
                raise ValueError("Duplicate or excessive ZIP entries")
            for m in members:
                kind = (m.external_attr >> 16) & 0o170000
                if (m.is_dir() or kind not in (0, stat.S_IFREG)
                        or m.file_size > MAX_MEMBER or m.compress_size == 0
                        or m.file_size > m.compress_size * 100):
                    raise ValueError("Unsafe ZIP member")
            if MANIFEST not in names:
                raise ValueError("Missing review-only manifest")
            manifest = json.loads(z.read(MANIFEST))
            if not isinstance(manifest, dict) or set(manifest) != META_KEYS:
                raise ValueError("Unexpected manifest")
            items = manifest["unit_templates"]
            original = report["unit_files"]
            if (manifest["format"] != "bob-v070-sanitized-service-review"
                    or manifest["version"] != 1 or manifest["deployable"] is not False
                    or manifest["warnings"] != WARNINGS or not isinstance(items, list)
                    or len(items) != manifest["source_count"]
                    or len(items) != len(original) or not 1 <= len(items) <= 120):
                raise ValueError("Invalid review status or count")
            expected_files = {MANIFEST}
            for i, (item, record) in enumerate(zip(items, original), 1):
                if not isinstance(item, dict) or set(item) != ITEM_KEYS:
                    raise ValueError("Unexpected template metadata")
                scope, unit, kind = item["scope"], item["unit"], item["kind"]
                if (scope not in {"user","system"} or unit not in EXPECTED_NAMES
                        or kind not in {"unit","dropin"}
                        or (scope,unit,kind) != (
                            record.get("scope"),record.get("unit"),record.get("kind"))
                        or item["raw_unit_sha256"] != record.get("sha256")):
                    raise ValueError("Source topology differs")
                basename = f"{i:03d}-{scope}-{unit}-{kind}.template.txt"
                if item["template"] != basename:
                    raise ValueError("Unexpected candidate name")
                path = "candidates/" + basename
                expected_files.add(path)
                if (not isinstance(item["safe_directive_keys"], list)
                        or not all(isinstance(k,str) for k in item["safe_directive_keys"])
                        or item["safe_directive_keys"] != sorted(set(item["safe_directive_keys"]))
                        or not isinstance(item["withheld_known_keys"],dict)
                        or any(k not in HIDDEN or type(v) is not int or v < 1 or v > 999999
                               for k,v in item["withheld_known_keys"].items())
                        or type(item["unclassified_directives_count"]) is not int
                        or not 0 <= item["unclassified_directives_count"] <= 999999):
                    raise ValueError("Unexpected safe-key metadata")
                audit_template(z.read(path), item)
            if set(names) != expected_files:
                raise ValueError("Unexpected ZIP membership")
    return len(items)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--topology-report", required=True, type=Path)
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as unprivileged operator")
    try:
        count = audit(args.archive, args.topology_report)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError,
            json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print("PRIVATE SERVICE CANDIDATE AUDIT REFUSED:", type(exc).__name__,
              "(no live files or services changed)", file=sys.stderr)
        return 1
    print("PRIVATE SERVICE CANDIDATE AUDIT: PASS")
    print("Candidates verified:", count)
    print("Source hashes matched the private topology report: YES")
    print("Archive membership, template grammar and review-only markers: PASS")
    print("Deployable: NO; manual review still required before sharing.")
    print("No source, services, credentials, Windows startup or SQLite changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
