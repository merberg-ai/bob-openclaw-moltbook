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
    # The existing R2 dashboard imports bob_v08.inspect FIRST, which caches
    # bob_v08.__path__ pointing exclusively at its Shadow4 ZIP. Python will
    # not discover R3 submodules just because sys.path now includes R3.
    # Admit this secondary archive only after verifying BOTH installed ZIPs.
    previous = sys.modules.get("bob_v08")
    if previous is not None:
        r2 = home/".local/bin/bob_v08_package.pyz"
        r2origin = str(r2)+"/bob_v08/__init__.py"
        if getattr(previous,"__file__",None) == r2origin:
            try:
                old = r2.lstat()
                old_digest = record["files"]["bob_v08_package.pyz"]
                if (not stat.S_ISREG(old.st_mode) or old.st_uid != uid
                        or old.st_mode & 0o077 or old.st_nlink != 1
                        or not 0 < old.st_size <= 512*1024
                        or not isinstance(old_digest,str)
                        or not re.fullmatch(r"[a-f0-9]{64}",old_digest)
                        or hashlib.sha256(r2.read_bytes()).hexdigest()
                        != old_digest):
                    raise ValueError("r3_legacy_shadow_archive_unverified")
            except (OSError,KeyError):
                raise ValueError("r3_legacy_shadow_archive_unavailable") from None
        elif getattr(previous,"__file__",None) != (
                str(file)+"/bob_v08/__init__.py"):
            raise ValueError("r3_existing_package_source_untrusted")
        paths = getattr(previous,"__path__",None)
        if not isinstance(paths,list):
            raise ValueError("r3_existing_package_path_untrusted")
        source = str(file)+"/bob_v08"
        if source not in paths:
            paths.insert(0,source)
    return "verified_registry_archive"
