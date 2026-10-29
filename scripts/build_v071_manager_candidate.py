#!/usr/bin/env python3
"""Build an isolated v0.7.1 UI candidate from the pinned v0.6 manager source.

No live install, web server, sockets, SQLite, systemd, Moltbook or credentials.
This produces an explicitly uninstalled two-file UI candidate: the existing
server with three GET response transforms and a responsive navigation module.
Original POST/auth/CSRF/origin/publisher logic remains byte-for-byte untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / "src/bin/bob-activity-manager"
NAVIGATION = HERE / "webui/navigation_shell.py"
PINNED_BASELINE_SHA256 = "9f75535bc013c9ea7ab7582e0adfad3e78d6a7ce769a5b14c66b949c5542e65c"
ROUTES = (
    ("/", "render()"),
    ("/activity", "activity_page()"),
    ("/originals", "originals_page()"),
)
MAX_BYTES = 128 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def candidate_source(source: bytes, navigation: bytes) -> bytes:
    if sha256(source) != PINNED_BASELINE_SHA256:
        raise ValueError("Original Activity Manager differs from pinned baseline")
    if not 0 < len(navigation) < MAX_BYTES:
        raise ValueError("Invalid navigation module size")
    compile(navigation, "navigation_shell.py", "exec")
    raw = source.decode("utf-8")
    marker = '\nDATA = Path.home() / ".config" / "moltbook"'
    if raw.count(marker) != 1:
        raise ValueError("Cannot locate exact import insertion point")
    raw = raw.replace(marker,
                      "\nfrom navigation_shell import integrate_existing_html\n"
                      + marker, 1)
    for path, renderer in ROUTES:
        anchor = f'self._send(200, {renderer}, "text/html; charset=utf-8")'
        replacement = (
            f'self._send(200, integrate_existing_html({renderer}, {path!r}),'
            ' "text/html; charset=utf-8")'
        )
        if raw.count(anchor) != 1:
            raise ValueError("Activity Manager route changed: " + path)
        raw = raw.replace(anchor, replacement, 1)
    candidate = raw.encode("utf-8")
    compile(candidate, "bob-activity-manager", "exec")
    # Changes must be restricted to the four known text replacements.
    if candidate.count(b"integrate_existing_html") != 4:
        raise ValueError("Unexpected UI integration count")
    return candidate


def build() -> tuple[bytes, bytes]:
    if SOURCE.is_symlink() or NAVIGATION.is_symlink():
        raise ValueError("Source symlinks refused")
    original = SOURCE.read_bytes()
    navigation = NAVIGATION.read_bytes()
    return candidate_source(original, navigation), navigation


def review_zip(candidate: bytes, nav: bytes) -> bytes:
    # Archive remains a development review artifact. This is not an installer.
    manifest = {
        "format": "bob-v071-navigation-review-v1",
        "deployable": False,
        "base_manager_sha256": PINNED_BASELINE_SHA256,
        "candidate_manager_sha256": sha256(candidate),
        "navigation_sha256": sha256(nav),
        "routes": [route for route, _ in ROUTES],
        "notes": "Only three GET HTML responses modified; all production services unchanged",
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bin/bob-activity-manager", candidate)
        archive.writestr("bin/navigation_shell.py", nav)
        archive.writestr("REVIEW-MANIFEST.json", json.dumps(manifest, sort_keys=True))
    return stream.getvalue()


def write_private_zip(data: bytes) -> Path:
    folder = Path.home() / ".local/state/bob-baseline/v071-candidates"
    if folder.is_symlink():
        raise ValueError("Symlink candidate folder refused")
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    if stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise PermissionError("Candidate folder must be private")
    name = "bob-v071-navigation-" + sha256(data)[:16] + ".zip"
    dest = folder / name
    fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(data)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-review-zip", action="store_true",
                        help="Write uninstalled candidate archive to private user-owned folder")
    args = parser.parse_args()
    try:
        candidate, navigation = build()
        archive = review_zip(candidate, navigation)
        if args.private_review_zip:
            path = write_private_zip(archive)
            print("Private, uninstalled UI candidate:", path)
    except (OSError, ValueError, RuntimeError, SyntaxError, UnicodeError) as exc:
        print("v0.7.1 UI BUILD REFUSED:", type(exc).__name__,
              "(live Bob unchanged)", file=sys.stderr)
        return 1
    print("v0.7.1 UI INTEGRATION BUILD: PASS")
    print("Rendered GET routes wrapped:", len(ROUTES))
    print("Original source fingerprint preserved:", sha256(SOURCE.read_bytes()) == PINNED_BASELINE_SHA256)
    print("Modified POST/auth/CSRF handlers: NO")
    print("Candidate files: 2; deployable: NO")
    print("No live service, network, credentials, or database changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
