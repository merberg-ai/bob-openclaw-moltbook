#!/usr/bin/env python3
"""CH-HTTPS4: operator-confirmed rotation of Bob's historical LAN password.

Without --apply this is READ ONLY. The only write is the existing locked,
atomic lan-auth.json password rotation. Never put passwords in argv, the
environment, shell history, a web endpoint, a log, a URL or this repository.
The installed CH-HTTPS3 release, R3 Off gates and HTTPS certificate must pass
before the credential can be changed. No services, timers, SQLite or publisher
permissions are touched.
"""
from __future__ import annotations

import base64
import getpass
from http.client import HTTPSConnection, HTTPException
import os
from pathlib import Path
import pwd
import ssl
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src/lib/bob")]
import bob_dashboard_auth as auth
import bob_release_updater as updater
import report_ch_https3_cutover as cutover

AUTH_FILE = Path.home() / ".config/bob-system/lan-auth.json"
CONFIRMATION = "ROTATE BOB HTTPS PASSWORD"


def _operator_account() -> bool:
    try:
        user = pwd.getpwuid(os.geteuid())
        return (os.geteuid() != 0 and user.pw_name == "openclaw"
                and user.pw_dir == str(Path.home()))
    except (KeyError, OSError):
        return False


def _ready() -> bool:
    """No credential reads or writes unless the installed TLS gate passes."""
    if not _operator_account():
        return False
    try:
        return (cutover.inspect("installed")["acceptance"] == "PASS"
                and bool(auth.load(AUTH_FILE)["username"]))
    except (OSError, ValueError, TypeError, KeyError, ssl.SSLError):
        return False


def _basic(username: str, password: str) -> str:
    return "Basic " + base64.b64encode(
        (username + ":" + password).encode("utf-8")
    ).decode("ascii")


def _https_get(authorization: str | None) -> tuple[int, bytes]:
    """Fixed loopback IP + trusted CA/IP SAN; no redirects, HTTP or proxy."""
    conn = HTTPSConnection(cutover.ADDRESS, cutover.PORT, timeout=6,
                           context=updater.manager_tls_context())
    try:
        headers = {"Host": "127.0.0.1:18790"}
        if authorization is not None:
            headers["Authorization"] = authorization
        conn.request("GET", "/r3", headers=headers)
        response = conn.getresponse()
        body = response.read(65537)
        return response.status, body
    finally:
        conn.close()


def _rotation_proven(path: Path, username: str, old: str, new: str) -> bool:
    """Verify old rejects, new works, anonymous rejects on LIVE verified TLS."""
    if (auth.authorized(path, _basic(username, old))
            or not auth.authorized(path, _basic(username, new))):
        return False
    try:
        old_status, _ = _https_get(_basic(username, old))
        new_status, new_page = _https_get(_basic(username, new))
        anonymous_status, _ = _https_get(None)
    except (OSError, ValueError, UnicodeError, ssl.SSLError, HTTPException):
        return False
    return (old_status == 401 and new_status == 200
            and 0 < len(new_page) <= 65536
            and b"Bob R3 Controls" in new_page
            and b"compiled locked" in new_page
            and anonymous_status == 401)


def _new_password_ok(current: str, replacement: str, confirmation: str) -> bool:
    """ASCII printable for predictable Windows browser Basic-auth encoding."""
    return (replacement == confirmation and replacement != current
            and auth.MIN_PASSWORD <= len(replacement) <= auth.MAX_PASSWORD
            and all(32 <= ord(ch) <= 126 for ch in replacement))


def rotate_and_verify(path: Path, old: str, new: str, confirmation: str) -> bool:
    """Return whether the credential change is fully proved, NOT whether written.

    Once auth.rotate succeeds, a postflight outage does not restore the exposed
    historical password. Console reset remains available for recovery.
    """
    if not _ready():
        raise auth.CredentialError("HTTPS preflight refused")
    if not _new_password_ok(old, new, confirmation):
        raise auth.CredentialError("invalid replacement password")
    username = auth.load(path)["username"]
    auth.rotate(path, old, new, confirmation)
    return (_rotation_proven(path, username, old, new)
            and _ready())


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args not in ([], ["--preflight"], ["--verify"], ["--apply"]):
        print("Usage: python3 scripts/ch_https4_rotate_dashboard.py "
              "[--preflight | --verify | --apply]")
        return 2
    if not _operator_account():
        print("CH-HTTPS4 REFUSED: expected openclaw non-root account")
        return 1
    if args != ["--apply"]:
        ready = _ready()
        print("CH-HTTPS4 HTTPS CREDENTIAL GATE (READ ONLY)")
        print("installed HTTPS, current login and R3 Off: "
              + ("PASS" if ready else "NOT_VERIFIED"))
        print("historical password rejection: only checked during --apply")
        print("changes to services, database, credentials or publishing: NONE")
        return 0 if ready else 1
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        print("CH-HTTPS4 REFUSED: interactive trusted terminal required")
        return 1
    if not _ready():
        print("CH-HTTPS4 REFUSED: installed HTTPS preflight NOT_VERIFIED")
        return 1
    print("This changes only the private LAN dashboard password.")
    print("Both Windows browsers must sign in again. R3 remains Off.")
    try:
        if input("Type " + CONFIRMATION + " to proceed: ").strip() != CONFIRMATION:
            print("CH-HTTPS4: declined; credentials unchanged")
            return 1
        old = getpass.getpass("Current dashboard password: ")
        new = getpass.getpass("New dashboard password (20-256 ASCII characters): ")
        confirmation = getpass.getpass("Confirm new dashboard password: ")
        verified = rotate_and_verify(AUTH_FILE, old, new, confirmation)
    except (OSError, EOFError, KeyboardInterrupt, ValueError,
            auth.CredentialError) as exc:
        # An I/O exception after an atomic rename can leave new credentials
        # installed. Never claim credentials are unchanged on an exception.
        print("CH-HTTPS4 REFUSED OR INDETERMINATE: " + type(exc).__name__)
        print("Do not retry blindly; check HTTPS, then use trusted console reset "
              "if needed. No secrets were printed.")
        return 1
    print("CH-HTTPS4 credential change: APPLIED")
    print("old password rejected + new password accepted over verified HTTPS: "
          + ("PASS" if verified else "NOT_VERIFIED"))
    print("installed TLS/R3 safeguard recheck: "
          + ("PASS" if verified else "CHECK REQUIRED"))
    print("No systemd, SQLite, publisher or Moltbook action performed.")
    if not verified:
        print("Do not assume old password remains usable or roll back to it. "
              "Use the trusted console reset if recovery is needed.")
    else:
        print("Reconnect both Windows browsers using a fresh private window.")
        print("Rerun --verify after the separately approved manager restart.")
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
