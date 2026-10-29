#!/usr/bin/env python3
"""End-to-end disposable regular-file install + real user-systemd rehearsal.

Opt-in transient test units only. Never addresses the production service.
"""
from __future__ import annotations
import argparse
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
import time

import rehearse_v071_regular_file_installer as installer
import rehearse_v071_user_systemd as units
import preview_v071_ui as preview
import build_v071_manager_candidate as builder

SCENARIOS = ("healthy", "failed-health", "restart-failure")


def child(root: Path, release: str):
    installer.safe(root)
    manager, nav = installer.files(root)
    baseline, candidate, navigation = installer.sealed(root)
    expected = candidate if release == "candidate" else baseline
    if manager.read_bytes() != expected:
        raise ValueError("child release mismatch")
    if release == "candidate" and nav.read_bytes() != navigation:
        raise ValueError("navigation mismatch")
    if Path.home().resolve() != (root / "home").resolve():
        raise ValueError("synthetic HOME required")
    loader = SourceFileLoader("v071_e2e_" + release, str(manager))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    seeded = root / "synthetic-seeded"
    if not seeded.exists():
        preview.seed_synthetic_views(module, root)
        installer.write_once(seeded, b"synthetic", 0o600)
    class ReadOnly(module.Handler):
        def do_POST(self):
            self._send(405, "Disposable read-only staging")
        def do_GET(self):
            if self.path not in preview.ROUTES:
                self._send(404, "Not found")
                return
            super().do_GET()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnly)
    module.ALLOWED_HOSTS = {f"127.0.0.1:{server.server_port}",
                            f"localhost:{server.server_port}"}
    try:
        installer.write_once(root / "port", str(server.server_port).encode(), 0o600)
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


def probe(root: Path, release: str):
    portfile = root / "port"
    if portfile.is_symlink() or not portfile.exists():
        return False
    try:
        port = int(portfile.read_text())
    except (OSError, ValueError):
        return False
    if not 1 <= port <= 65535:
        return False
    for route in ("/healthz", "/", "/activity", "/originals"):
        conn = HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            conn.request("GET", route)
            reply = conn.getresponse()
            body = reply.read(256 * 1024)
            if reply.status != 200:
                return False
            if release == "candidate" and route != "/healthz" and b"bob-layout" not in body:
                return False
            if release == "baseline" and route == "/" and b"Preview: an imaginary discussion" not in body:
                return False
        except (OSError, TimeoutError):
            return False
        finally:
            conn.close()
    conn = HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("POST", "/originals/request/intro", body=b"denied")
        reply = conn.getresponse()
        reply.read()
        return reply.status == 405
    except (OSError, TimeoutError):
        return False
    finally:
        conn.close()


def start(root: Path, release: str, name: str):
    if not units.safe_unit(name) or release not in ("candidate", "baseline"):
        raise ValueError("unsafe transient target")
    units.absent(name)
    cmd = ["systemd-run", "--user", "--collect", "--quiet",
           "--unit=" + name, "--property=Type=exec",
           "--property=WorkingDirectory=" + str(root),
           "--setenv=HOME=" + str(root / "home"),
           "--setenv=PYTHONPATH=" + os.pathsep.join((
               str(root / "bin"), str(builder.HERE / "src/lib/bob"))),
           "--setenv=PYTHONDONTWRITEBYTECODE=1",
           "--setenv=BOB_MANAGER_BIND=127.0.0.1",
           "--setenv=BOB_MANAGER_PORT=0",
           sys.executable, str(Path(__file__).resolve()),
           "--child-root", str(root), "--release", release]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            timeout=12, check=False, env=units.command_env())
    if result.returncode:
        raise ValueError("transient start rejected")
    for _ in range(20):
        if probe(root, release):
            status = units.systemctl("show", name, "--property=ActiveState", "--no-pager")
            return status.returncode == 0 and status.stdout.strip() == "ActiveState=active"
        time.sleep(0.2)
    return False


def stop(name: str):
    if not units.safe_unit(name):
        raise ValueError("unsafe stop target")
    response = units.systemctl("stop", name)
    if response.returncode:
        raise RuntimeError("transient cleanup failed")


def run(scenario):
    if scenario not in SCENARIOS or os.geteuid() == 0:
        raise ValueError("invalid scenario or root")
    root, temporary = installer.stage()
    first = units.UNIT_PREFIX + secrets.token_hex(6) + ".service"
    second = units.UNIT_PREFIX + secrets.token_hex(6) + ".service"
    try:
        (root / "home/.config/moltbook").mkdir(mode=0o700, parents=True)
        installer.install(root)
        try:
            if scenario != "restart-failure" and not start(root, "candidate", first):
                raise RuntimeError("candidate_health_or_active_state")
            candidate_ok = scenario != "restart-failure"
        finally:
            if scenario != "restart-failure":
                try:
                    stop(first)
                except RuntimeError as exc:
                    raise RuntimeError("candidate_unit_cleanup") from exc
        (root / "port").unlink(missing_ok=True)
        if scenario == "healthy" and candidate_ok:
            installer.finish(root)
            outcome, baseline_ok = "candidate_healthy", "not_needed"
        else:
            try:
                installer.recover(root)
            except (OSError, ValueError, RuntimeError) as exc:
                raise RuntimeError("file_rollback_failed") from exc
            try:
                try:
                    if not start(root, "baseline", second):
                        raise RuntimeError("baseline_health_or_active_state")
                    baseline_ok = True
                except (OSError, ValueError, RuntimeError) as exc:
                    raise RuntimeError("baseline_start_or_health") from exc
            finally:
                try:
                    stop(second)
                except RuntimeError as exc:
                    raise RuntimeError("baseline_unit_cleanup") from exc
            outcome = "baseline_recovered"
        manager, nav = installer.files(root)
        base, candidate, navigation = installer.sealed(root)
        expected = candidate if scenario == "healthy" else base
        if manager.read_bytes() != expected or nav.exists() != (scenario == "healthy"):
            raise AssertionError("files not correctly restored")
        db = root / "home/.config/moltbook/activity-queue.sqlite3"
        with sqlite3.connect(db) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        if not integrity:
            raise AssertionError("synthetic SQLite integrity failed")
        return {"outcome": outcome, "candidate_http": candidate_ok,
                "baseline_http": baseline_ok, "regular_file_restore": True,
                "synthetic_sqlite_integrity": integrity}
    finally:
        temporary.cleanup()


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
        print("v0.7.1 END-TO-END SYSTEMD INSTALL: PLAN ONLY")
        return 0
    try:
        report = run(args.scenario)
    except (OSError, RuntimeError, ValueError, AssertionError, sqlite3.Error,
            subprocess.TimeoutExpired) as exc:
        code = str(exc) if isinstance(exc, RuntimeError) and str(exc) in {
            "candidate_health_or_active_state", "candidate_unit_cleanup",
            "file_rollback_failed", "baseline_start_or_health",
            "baseline_unit_cleanup"} else "unclassified"
        print("v0.7.1 END-TO-END SYSTEMD INSTALL: REFUSED", type(exc).__name__)
        print("safe_failure_phase:", code)
        return 1
    print("v0.7.1 END-TO-END SYSTEMD INSTALL: PASS")
    for k, v in report.items():
        print(k + ":", v)
    print("production_executor_available: NO; live_service_targeted: NO")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
