"""R3.13b read-only installed publisher executable/source attestation.

The only unit read is systemctl --user cat for the exact existing publisher
service/timer. Never print the command, path, SHA, unit body or environment.
The current v0.7 executable is NOT assumed to equal the unreleased next
source candidate. A matched hash isn't new R3 authorization.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import stat

from .r313a_private_migration import _private

# scripts/ is injected by the fixed CLI. This module has no systemd actions.
from report_r38_effective_units import (
    SERVICE, TIMER, _cat, _effective, _safe_executable, audit,
)

MAX_EXEC_BYTES = 512 * 1024


def _exec_path(unit_text: str) -> Path:
    entries, _ = _effective(unit_text, "Service")
    commands = []
    for key, value in entries:
        if key == "ExecStart":
            if not value:
                commands = []
            else:
                commands.append(value)
    if len(commands) != 1 or not _safe_executable(commands[0]):
        raise ValueError("publisher_exec_not_trusted")
    argv = shlex.split(commands[0], posix=True)
    target = Path(argv[-1])
    if (not target.is_absolute() or target.name != "bob-moltbook-publisher"
            or not target.parts[0] == "/" or ".." in target.parts):
        raise ValueError("publisher_exec_not_absolute")
    return target


def _safe_binary(path: Path, *, uid: int) -> bytes:
    """Read single owner/root-controlled regular file without symlink traversal."""
    for ancestor in (path, *list(path.parents)[:-1]):
        try:
            row = ancestor.lstat()
        except OSError:
            raise ValueError("publisher_file_unavailable") from None
        if stat.S_ISLNK(row.st_mode):
            raise ValueError("publisher_path_symlink")
        if row.st_uid not in (0, uid) or row.st_mode & 0o022:
            raise ValueError("publisher_path_writable_or_other_owner")
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("publisher_not_regular_file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        row = os.fstat(fd)
        if (not stat.S_ISREG(row.st_mode) or row.st_size <= 0
                or row.st_size > MAX_EXEC_BYTES or row.st_nlink != 1
                or row.st_uid not in (0, uid) or row.st_mode & 0o022):
            raise ValueError("publisher_file_untrusted")
        data = bytearray()
        while len(data) <= MAX_EXEC_BYTES:
            part = os.read(fd, min(65536, MAX_EXEC_BYTES + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        end = os.fstat(fd)
        if (len(data) != row.st_size or b"\x00" in data or
                end.st_ino != row.st_ino or end.st_size != row.st_size or
                end.st_mtime_ns != row.st_mtime_ns):
            raise ValueError("publisher_file_changed_during_read")
        return bytes(data)
    finally:
        os.close(fd)


def _registry_match(path: Path, contents: bytes, *, home: Path, uid: int) -> str:
    """Updater registry is evidence only if target and registry hash agree."""
    registry = home / ".local/state/bob-updater/installed.json"
    try:
        if path != home / ".local/bin/bob-moltbook-publisher":
            return "not_registry_target"
        if not _private(registry, directory=False, uid=uid):
            return "registry_unavailable"
        if registry.stat().st_size > 32768:
            return "registry_unverified"
        data = json.loads(registry.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("format") != "bob-updater-v1":
            return "registry_unverified"
        files = data.get("files")
        if not isinstance(files, dict):
            return "registry_unverified"
        sha = files.get("bob-moltbook-publisher")
        if sha is None:
            return "not_registry_tracked"
        if not isinstance(sha, str) or len(sha) != 64:
            return "registry_unverified"
        return ("verified_registry_hash" if hashlib.sha256(contents).hexdigest() == sha
                else "registry_hash_mismatch")
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return "registry_unverified"


def attest(*, unit_reader=_cat, uid: int, home: Path,
           candidate_source: Path | None = None) -> dict:
    """Never trusts user-supplied service names; candidates are comparison only."""
    result = {
        "format": "bob-r313b-installed-publisher-attestation-v1",
        "effective_unit_shape": "unverified",
        "installed_file": "unverified",
        "updater_registry": "unverified",
        "current_next_candidate_match": "unverified",
        "review_blockers": [],
        "installed_r3_capability": "not_attested",
        "cutover_authorized": False,
    }
    try:
        service = unit_reader(SERVICE)
        timer = unit_reader(TIMER)
        check = audit(service, timer)
        if check.blockers or not (check.service_valid and check.timer_valid):
            raise ValueError("publisher_effective_unit_not_reviewed")
        result["effective_unit_shape"] = "reviewed_shape"
        path = _exec_path(service)
        contents = _safe_binary(path, uid=uid)
        result["installed_file"] = "owner_controlled_regular"
        result["updater_registry"] = _registry_match(
            path, contents, home=Path(home), uid=uid)
        if result["updater_registry"] == "registry_hash_mismatch":
            raise ValueError("publisher_registry_hash_drift")
        if candidate_source is not None:
            candidate = Path(candidate_source)
            # A repo checkout is only a comparative candidate, not a
            # signature or a trusted install manifest.
            if candidate.name == "bob-moltbook-publisher" and (
                    candidate.is_file() and not candidate.is_symlink() and
                    candidate.stat().st_size <= MAX_EXEC_BYTES):
                result["current_next_candidate_match"] = (
                    "same_bytes" if hashlib.sha256(contents).digest() ==
                    hashlib.sha256(candidate.read_bytes()).digest()
                    else "different_legacy_release_expected")
    except (OSError, ValueError, TypeError):
        result["review_blockers"].append(
            "installed_publisher_source_or_unit_needs_review")
    # A clean file/registry still does not prove runtime credentials,
    # consent, production readiness or a reviewed R3 installed release.
    return result
