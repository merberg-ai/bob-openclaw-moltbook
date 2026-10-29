#!/usr/bin/env python3
"""Reset Bob's LAN dashboard username/password from the trusted local console.

Interactive only: never accepts passwords in CLI arguments, environment or files.
Uses the same private rotation lock as the dashboard Settings form, so changes
take effect immediately on deployed v0.7.2 without any systemd restart.
"""
from __future__ import annotations

import argparse
import fcntl
import getpass
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/lib/bob"))
from bob_dashboard_auth import CredentialError, MIN_PASSWORD, MAX_PASSWORD, load, authorized

AUTH_FILE = Path.home() / ".config/bob-system/lan-auth.json"
USERNAME = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")


def reset_login(path: Path, username: str, password: str):
    """Fail-closed, locked, atomic, private update of existing LAN credentials."""
    if not isinstance(username, str) or not USERNAME.fullmatch(username):
        raise CredentialError("username must use 1-64 letters, digits, dot, underscore or dash")
    if (not isinstance(password, str) or not MIN_PASSWORD <= len(password) <= MAX_PASSWORD
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in password)):
        raise CredentialError("password must contain 20-256 printable characters")
    if path.is_symlink():
        raise CredentialError("credential path is a symlink")
    lockpath = path.with_name(".lan-auth-rotation.lock")
    if lockpath.is_symlink():
        raise CredentialError("credential lock is a symlink")
    lockfd = os.open(lockpath, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    pending = None
    try:
        lockinfo = os.fstat(lockfd)
        if (not stat.S_ISREG(lockinfo.st_mode) or lockinfo.st_uid != os.getuid()
                or stat.S_IMODE(lockinfo.st_mode) & 0o077):
            raise CredentialError("unsafe rotation lock")
        fcntl.flock(lockfd, fcntl.LOCK_EX)
        record = load(path)
        record["username"] = username
        record["password"] = password
        encoded = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        fd, name = tempfile.mkstemp(prefix=".lan-auth-console-", dir=path.parent)
        pending = Path(name)
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        load(path)  # re-validate original path and permissions under lock
        os.replace(pending, path)
        pending = None
        dirfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        # Do not print or return the credentials.
        if not authorized(path, "Basic " + __import__("base64").b64encode(
                (username + ":" + password).encode("utf-8")).decode("ascii")):
            raise CredentialError("new credential verification failed")
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)
        os.close(lockfd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run as the openclaw user, not root")
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        print("REFUSED: interactive terminal required", file=sys.stderr)
        return 1
    try:
        existing = load(AUTH_FILE)
        previous_username = existing["username"]
        username = input("Dashboard username [" + previous_username + "]: ").strip() or previous_username
        password = getpass.getpass("New dashboard password (20+ characters): ")
        confirmation = getpass.getpass("Confirm new password: ")
        if password != confirmation:
            raise CredentialError("password confirmation does not match")
        reset_login(AUTH_FILE, username, password)
    except (OSError, EOFError, KeyboardInterrupt, CredentialError, ValueError) as exc:
        print("Dashboard login unchanged:", type(exc).__name__, file=sys.stderr)
        return 1
    print("Dashboard login updated. Old login is now invalid; no restart needed.")
    print("For phone/desktop Basic Auth caching, use a new private tab to sign in again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
