#!/usr/bin/env python3
"""Disposable REAL systemd candidate-to-original-manager rollback, opt-in only.

Starts the generated two-file candidate and the exact SHA-pinned original
manager in separate transient units, in sequence. Both use one synthetic HOME
and synthetic SQLite. Publishing is disabled in both. Never contacts live Bob.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
import importlib.util
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time

import build_v071_manager_candidate as builder
import preview_v071_ui as preview
from rehearse_v071_ui_update import inspect_package
import rehearse_v071_user_systemd as units

SCENARIOS = ("healthy", "failed-health")
PREFIX = "bob-v071-preview-"


def prepare(root: Path):
    preview.prepare(root)
    baseline = builder.SOURCE.read_bytes()
    if builder.sha256(baseline) != builder.PINNED_BASELINE_SHA256:
        raise ValueError("original manager drift")
    preview.save(root / "baseline" / "bob-activity-manager", baseline, 0o700)
    candidate, navigation = builder.build()
    inspect_package(builder.review_zip(candidate, navigation))
    if (root / "bin/bob-activity-manager").read_bytes() != candidate:
        raise ValueError("candidate changed")
    return root


def load_manager(path: Path, name: str):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def child(root: Path, release: str):
    if release not in ("candidate", "baseline"):
        raise ValueError("unknown release")
    preview.assert_private(root)
    if Path.home().resolve() != (root / "home").resolve():
        raise ValueError("not synthetic HOME")
    if release == "baseline":
        original = root / "baseline/bob-activity-manager"
        if original.is_symlink() or builder.sha256(original.read_bytes()) != builder.PINNED_BASELINE_SHA256:
            raise ValueError("baseline checksum mismatch")
        module = load_manager(original, "bob_v071_actual_baseline")
    else:
        module = load_manager(root / "bin/bob-activity-manager", "bob_v071_real_candidate")
    # Seed only once. The second service must preserve the first service's rows.
    marker = root / "seeded"
    if not marker.exists():
        preview.seed_synthetic_views(module, root)
        preview.save(marker, b"synthetic-only")
    class ReadOnly(module.Handler):
        def do_POST(self):
            self._send(405, "Publishing disabled in disposable rollback rehearsal")
        def do_GET(self):
            if self.path not in ("/", "/activity", "/originals", "/healthz"):
                self._send(404, "Unknown synthetic route")
                return
            super().do_GET()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnly)
    module.ALLOWED_HOSTS = {f"127.0.0.1:{server.server_port}", f"localhost:{server.server_port}"}
    portfile = root / ("port-" + release)
    try:
        preview.save(portfile, str(server.server_port).encode())
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


def healthy(root: Path, release: str) -> bool:
    try:
        port = int((root / ("port-" + release)).read_text())
    except (OSError, ValueError):
        return False
    if not 1 <= port <= 65535:
        return False
    for route in ("/healthz", "/", "/activity", "/originals"):
        connection = HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            connection.request("GET", route)
            response = connection.getresponse()
            body = response.read(256 * 1024)
            if response.status != 200 or (route != "/healthz" and\n                (b"bob-layout" not in body if release == "candidate"\n                 else b"Preview: an imaginary discussion" not in body and\n                      b"Synthetic reply" not in body and\n                      b"original" not in body.lower())):
                return False
        except (OSError, TimeoutError):
            return False
        finally:
            connection.close()
    connection = HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("POST", "/originals/request/intro", body=b"no")
        response = connection.getresponse()
        return response.status == 405
    except (OSError, TimeoutError):
        return False
    finally:
        connection.close()


def launch(root: Path, release: str, unit: str):
    if not units.safe_unit(unit) or release not in ("candidate", "baseline"):
        raise ValueError("unsafe transient target")
    units.absent(unit)
    command = ["systemd-run", "--user", "--collect", "--quiet",
               "--unit=" + unit, "--property=Type=exec",
               "--property=WorkingDirectory=" + str(root),
               "--setenv=HOME=" + str(root / "home"),
               "--setenv=PYTHONPATH=" + os.pathsep.join((
                   str(root / "bin"), str(builder.HERE / "src/lib/bob"))),
               "--setenv=PYTHONDONTWRITEBYTECODE=1",
               "--setenv=BOB_MANAGER_BIND=127.0.0.1",
               "--setenv=BOB_MANAGER_PORT=0",
               sys.executable, str(Path(__file__).resolve()),
               "--child-root", str(root), "--release", release]
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=12, check=False, env=units.command_env())
    if result.returncode:
        raise RuntimeError("transient start refused")
    for _ in range(20):
        if healthy(root, release):
            status = units.systemctl("show", unit, "--property=ActiveState", "--no-pager")
            return status.returncode == 0 and status.stdout.strip() == "ActiveState=active"
        time.sleep(0.2)
    return False


def database_ok(root: Path) -> bool:
    with closing(sqlite3.connect(root / "home/.config/moltbook/activity-queue.sqlite3")) as db:
        return db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def execute(scenario: str):
    if scenario not in SCENARIOS or os.geteuid() == 0:
        raise ValueError("unapproved scenario/user")
    with tempfile.TemporaryDirectory(prefix=PREFIX) as temp:
        root = prepare(Path(temp))
        first = units.UNIT_PREFIX + secrets.token_hex(6) + ".service"
        second = units.UNIT_PREFIX + secrets.token_hex(6) + ".service"
        try:
            if not launch(root, "candidate", first):
                raise RuntimeError("candidate startup or health refused")
            candidate_healthy = True
        finally:
            units.systemctl("stop", first)
        if scenario == "healthy":
            return {"outcome": "candidate_healthy", "candidate_http": candidate_healthy,
                    "baseline_http": "not_needed", "synthetic_sqlite_integrity": database_ok(root)}
        # Deliberately inject a failure verdict, even though candidate passed
        # actual HTTP checks. Recover using original manager code, not fixture.
        try:
            if not launch(root, "baseline", second):
                raise RuntimeError("original manager recovery HTTP refused")
            recovered = True
        finally:
            units.systemctl("stop", second)
        return {"outcome": "original_manager_recovered", "candidate_http": candidate_healthy,
                "baseline_http": recovered, "synthetic_sqlite_integrity": database_ok(root)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execute-transient", action="store_true")
    p.add_argument("--scenario", choices=SCENARIOS, default="failed-health")
    p.add_argument("--child-root", type=Path, help=argparse.SUPPRESS)
    p.add_argument("--release", choices=("candidate", "baseline"), help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.child_root:
        child(args.child_root, args.release)
        return 0
    if not args.execute_transient:
        print("v0.7.1 ORIGINAL MANAGER ROLLBACK: PLAN ONLY")
        return 0
    try:
        result = execute(args.scenario)
        if not result["synthetic_sqlite_integrity"]:
            raise ValueError("synthetic database integrity refused")
    except (OSError, ValueError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired) as exc:
        print("v0.7.1 ORIGINAL MANAGER ROLLBACK: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 ORIGINAL MANAGER ROLLBACK: PASS")
    for key, value in result.items():
        print(key + ":", value)
    print("Only disposable user units; no production installer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
