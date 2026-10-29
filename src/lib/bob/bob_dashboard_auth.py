"""Private dashboard LAN credential store for v0.7.2.

No network, no service restarts, no password output. Reads from disk on each
authentication attempt so rotation invalidates the old credential immediately.
"""
from __future__ import annotations
import base64
import fcntl
import hmac
import json
import os
from pathlib import Path
import stat
import tempfile

MIN_PASSWORD = 20
MAX_PASSWORD = 256

class CredentialError(ValueError):
    pass

def _private(path: Path):
    if path.is_symlink() or not path.is_file():
        raise CredentialError("credential file unavailable")
    info = path.stat()
    directory = path.parent
    parent = directory.stat()
    if (directory.is_symlink() or info.st_uid != os.getuid() or
            parent.st_uid != os.getuid() or
            stat.S_IMODE(info.st_mode) & 0o077 or
            stat.S_IMODE(parent.st_mode) & 0o077 or info.st_size > 4096):
        raise CredentialError("unsafe credential permissions")

def load(path: Path):
    _private(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise CredentialError("invalid credential file") from exc
    if (not isinstance(value, dict) or
            not isinstance(value.get("username"), str) or
            not value["username"] or
            not isinstance(value.get("password"), str) or
            not MIN_PASSWORD <= len(value["password"]) <= MAX_PASSWORD):
        raise CredentialError("invalid credentials")
    return value

def authorized(path: Path, authorization: str):
    # Fail closed on any read or filesystem error, never fall back to no auth.
    try:
        creds = load(path)
        scheme, encoded = authorization.split(" ", 1)
        if scheme.lower() != "basic":
            return False
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        username, password = decoded.split(":", 1)
        return (hmac.compare_digest(username, creds["username"]) &
                hmac.compare_digest(password, creds["password"])) == 1
    except (CredentialError, OSError, ValueError, UnicodeError):
        return False

def rotate(path: Path, current: str, replacement: str, confirmation: str):
    if (not all(isinstance(v, str) for v in (current, replacement, confirmation))
            or not MIN_PASSWORD <= len(replacement) <= MAX_PASSWORD
            or replacement != confirmation or replacement == current
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in replacement)):
        raise CredentialError("invalid new password")
    # Lock independent of inode: os.replace never changes the lock inode.
    lock_path = path.with_name(".lan-auth-rotation.lock")
    if lock_path.is_symlink():
        raise CredentialError("unsafe credential lock")
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    staging = None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid != os.getuid():
            raise CredentialError("unsafe credential lock")
        fcntl.flock(fd, fcntl.LOCK_EX)
        creds = load(path)
        if not hmac.compare_digest(creds["password"], current):
            raise CredentialError("current password incorrect")
        creds["password"] = replacement
        payload = (json.dumps(creds, sort_keys=True) + "\n").encode("utf-8")
        tmpfd, name = tempfile.mkstemp(prefix=".lan-auth-next-", dir=path.parent)
        staging = Path(name)
        with os.fdopen(tmpfd, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        _private(path)  # Refuse unexpected changes before replacement.
        os.replace(staging, path)
        staging = None
        dirfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)
        os.close(fd)
