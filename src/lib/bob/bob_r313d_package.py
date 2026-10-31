"""Verify versioned R3 Python archive against installed updater registry.

Imported by the authenticated Activity Manager and local Bob proposal launcher,
not by the legacy publisher when production R3 remains source-gated Off.
Never fetch or install packages, read secrets, mutate settings or send HTTP.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys

ARCHIVE = "bob_r3_package.pyz"
FORMAT = "bob-updater-v1"


def load_verified() -> str:
    """Install local ZIP import path only if verified *installed* bytes match."""
    home = Path.home()
    uid = os.geteuid()
    if uid == 0 or pwd.getpwuid(uid).pw_dir != str(home):
        raise ValueError("r3_package_account_untrusted")
    file = home/".local/bin"/ARCHIVE
    registry = home/".local/state/bob-updater/installed.json"
    # Refuse symlinked/writable ancestors before reading either file.
    for folder in (home, home/".local", home/".local/bin",
                   home/".local/state", home/".local/state/bob-updater"):
        try:
            info = folder.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,uid)
                    or info.st_mode & 0o022):
                raise ValueError("r3_package_untrusted_ancestor")
        except OSError:
            raise ValueError("r3_package_ancestor_missing") from None
    for path,limit in ((file,512*1024),(registry,32768)):
        try:
            meta = path.lstat()
            if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != uid
                    or meta.st_mode & 0o077 or meta.st_nlink != 1
                    or not 0 < meta.st_size <= limit):
                raise ValueError("untrusted_r3_archive_or_registry")
        except OSError:
            raise ValueError("r3_package_not_installed") from None
    try:
        record = json.loads(registry.read_text(encoding="utf-8"))
        expected = record["files"][ARCHIVE]
        if (record.get("format") != FORMAT or not isinstance(expected,str)
                or not re.fullmatch(r"[a-f0-9]{64}",expected)):
            raise ValueError("r3_package_not_tracked")
        contents = file.read_bytes()
        if hashlib.sha256(contents).hexdigest() != expected:
            raise ValueError("r3_package_hash_mismatch")
    except (OSError,KeyError,TypeError,UnicodeError,json.JSONDecodeError):
        raise ValueError("r3_package_registry_unverified") from None
    if str(file) not in sys.path:
        sys.path.insert(0,str(file))
    return "verified_registry_archive"
