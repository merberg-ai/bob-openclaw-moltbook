#!/usr/bin/env python3
"""v0.7.1 UI release package + disposable atomic upgrade/rollback rehearsal.

Offline only: NOT a production installer. Original Bob binaries, services,
SQLite, credentials, startup settings and all network connections untouched.
"""
from __future__ import annotations

from contextlib import closing
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import zipfile

import build_v071_manager_candidate as builder

MARKER = "bob-v071-ui-staging-v1"
MAX_ARCHIVE = 512 * 1024
EXPECTED = {"bin/bob-activity-manager", "bin/navigation_shell.py", "REVIEW-MANIFEST.json"}


def inspect_package(raw: bytes) -> tuple[bytes, bytes]:
    if not 0 < len(raw) <= MAX_ARCHIVE:
        raise ValueError("UI package size refused")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        names = [item.filename for item in members]
        if set(names) != EXPECTED or len(names) != len(EXPECTED):
            raise ValueError("Invalid UI package membership")
        for item in members:
            kind = item.external_attr >> 16 & 0o170000
            if (item.is_dir() or kind not in (0, stat.S_IFREG)
                    or item.file_size > 128 * 1024 or item.compress_size < 1):
                raise ValueError("Unsafe UI package member")
        manifest = json.loads(archive.read("REVIEW-MANIFEST.json"))
        manager = archive.read("bin/bob-activity-manager")
        navigation = archive.read("bin/navigation_shell.py")
    if (not isinstance(manifest, dict) or set(manifest) != {
            "format", "deployable", "base_manager_sha256",
            "candidate_manager_sha256", "navigation_sha256", "routes", "notes"}
            or manifest.get("format") != "bob-v071-navigation-review-v1"
            or manifest.get("deployable") is not False
            or manifest.get("base_manager_sha256") != builder.PINNED_BASELINE_SHA256
            or manifest.get("candidate_manager_sha256") != builder.sha256(manager)
            or manifest.get("navigation_sha256") != builder.sha256(navigation)
            or manifest.get("routes") != ["/", "/activity", "/originals"]):
        raise ValueError("UI package manifest or checksum refused")
    baseline = builder.SOURCE.read_bytes()
    if manager != builder.candidate_source(baseline, navigation):
        raise ValueError("UI package does not match pinned baseline integration")
    compile(manager, "bin/bob-activity-manager", "exec")
    compile(navigation, "bin/navigation_shell.py", "exec")
    return manager, navigation


def save(root: Path, relative: str, data: bytes, mode: int) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ValueError("Unexpected pre-existing stage file")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def make_stage(root: Path, baseline: bytes, manager: bytes, navigation: bytes) -> None:
    if (root.is_symlink() or not root.name.startswith("bob-v071-ui-")
            or not root.is_dir() or list(root.iterdir())
            or stat.S_IMODE(root.stat().st_mode) & 0o077):
        raise ValueError("Unsafe or nonempty staging sandbox")
    if builder.sha256(baseline) != builder.PINNED_BASELINE_SHA256:
        raise ValueError("Baseline changed")
    save(root, "STAGING-ONLY", MARKER.encode(), 0o600)
    for label, contents in (
        ("baseline", {"bin/bob-activity-manager": baseline}),
        ("candidate", {"bin/bob-activity-manager": manager,
                       "bin/navigation_shell.py": navigation}),
    ):
        location = "releases/" + label
        for relative, data in contents.items():
            save(root, location + "/" + relative, data,
                 0o700 if relative.endswith("bob-activity-manager") else 0o600)
        save(root, location + "/SHA256.json", json.dumps(
            {name: hashlib.sha256(data).hexdigest()
             for name, data in sorted(contents.items())}, sort_keys=True
        ).encode(), 0o600)
    save(root, "state/synthetic.sqlite3.init", b"synthetic-only", 0o600)
    with closing(sqlite3.connect(root / "state/synthetic.sqlite3")) as db:
        db.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, phase TEXT NOT NULL)")
        db.execute("INSERT INTO events (phase) VALUES ('before')")
        db.commit()
    (root / "state/synthetic.sqlite3").chmod(0o600)


def validate_release(root: Path, label: str) -> None:
    if label not in {"baseline", "candidate"}:
        raise ValueError("Unrecognized release")
    folder = root / "releases" / label
    manifest_file = folder / "SHA256.json"
    if manifest_file.is_symlink() or not manifest_file.is_file():
        raise ValueError("Unsafe release manifest")
    manifest = json.loads(manifest_file.read_text())
    expected = {"bin/bob-activity-manager"}
    if label == "candidate":
        expected.add("bin/navigation_shell.py")
    if set(manifest) != expected:
        raise ValueError("Invalid release fileset")
    for relative, digest in manifest.items():
        file = folder / relative
        if (file.is_symlink() or not file.is_file()
                or hashlib.sha256(file.read_bytes()).hexdigest() != digest):
            raise ValueError("Tampered release content")


def switch(root: Path, label: str) -> None:
    validate_release(root, label)
    current = root / "current"
    if current.exists() and not current.is_symlink():
        raise ValueError("Non-symlink release pointer")
    if current.is_symlink() and os.readlink(current) not in {
            "releases/baseline", "releases/candidate"}:
        raise ValueError("Unexpected active release pointer")
    pending = root / ".pending-release"
    if pending.exists() or pending.is_symlink():
        raise ValueError("Stale pending pointer")
    try:
        pending.symlink_to("releases/" + label)
        os.replace(pending, current)
    finally:
        if pending.is_symlink():
            pending.unlink()


def active(root: Path) -> str:
    current = root / "current"
    if not current.is_symlink():
        raise ValueError("Missing release pointer")
    link = os.readlink(current)
    if link not in {"releases/baseline", "releases/candidate"}:
        raise ValueError("Untrusted release pointer")
    return link.rsplit("/", 1)[-1]


def rehearsal(root: Path, baseline: bytes, manager: bytes, navigation: bytes) -> dict:
    make_stage(root, baseline, manager, navigation)
    switch(root, "baseline")
    if active(root) != "baseline":
        raise AssertionError("Baseline selection failed")
    switch(root, "candidate")
    if active(root) != "candidate":
        raise AssertionError("UI candidate selection failed")
    with closing(sqlite3.connect(root / "state/synthetic.sqlite3")) as db:
        db.execute("INSERT INTO events (phase) VALUES ('after')")
        db.commit()
    # The simulated health check fails; rollback code, NOT new database writes.
    health_passed = False
    if not health_passed:
        switch(root, "baseline")
    if active(root) != "baseline":
        raise AssertionError("Failed health rollback did not restore baseline")
    validate_release(root, "baseline")
    validate_release(root, "candidate")
    with closing(sqlite3.connect(root / "state/synthetic.sqlite3")) as db:
        events = [row[0] for row in db.execute("SELECT phase FROM events ORDER BY id")]
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    if events != ["before", "after"] or integrity != "ok":
        raise AssertionError("Rollback damaged synthetic state")
    return {
        "package_verified": True,
        "source_baseline_pinned": True,
        "candidate_files": 2,
        "atomic_switch_verified": True,
        "failed_health_rollback_verified": True,
        "post_update_writes_preserved": True,
        "all_files_temp_only": True,
        "live_install_modified": False,
    }


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        candidate, nav = builder.build()
        raw = builder.review_zip(candidate, nav)
        verified_manager, verified_nav = inspect_package(raw)
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as temp:
            result = rehearsal(Path(temp), builder.SOURCE.read_bytes(),
                               verified_manager, verified_nav)
    except (OSError, ValueError, RuntimeError, SyntaxError, AssertionError,
            json.JSONDecodeError, zipfile.BadZipFile, sqlite3.Error) as exc:
        print("v0.7.1 UI RELEASE REHEARSAL: REFUSED", type(exc).__name__,
              "(live Bob unchanged)", file=sys.stderr)
        return 1
    print("v0.7.1 UI RELEASE REHEARSAL: PASS")
    for key, value in result.items():
        print(" ", key + ":", value)
    print("Temporary releases, symlink and synthetic database removed.")
    print("Nothing installed, restarted, enabled, published or changed in production.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
