#!/usr/bin/env python3
"""Opt-in REAL user-systemd two-file candidate acceptance and synthetic rollback.

No live Bob operations. The candidate is the actual generated manager + navigation
module, loaded inside the existing read-only preview harness with a fake HOME.
The rollback recovery service is an independent synthetic fixture, NOT a
production baseline-manager restart. No production mode exists.
"""
from __future__ import annotations

import argparse
from http.client import HTTPConnection
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time

import preview_v071_ui as preview
import build_v071_manager_candidate as builder
import rehearse_v071_user_systemd as units

SCENARIOS = ("healthy", "failed-health")
LIVE_UNIT = "bob-activity-manager.service"


def port_ready(path: Path) -> int | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = int(path.read_text().strip())
    except (ValueError, OSError):
        return None
    return value if 1 <= value <= 65535 else None


def preview_probe(port: int) -> bool:
    for route in ("/healthz", "/", "/activity", "/originals"):
        connection = HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            connection.request("GET", route)
            response = connection.getresponse()
            body = response.read(256 * 1024)
            if response.status != 200:
                return False
            if route != "/healthz" and (b'bob-layout' not in body
                                        or b'DEMO PREVIEW ONLY' not in body):
                return False
        except (OSError, TimeoutError):
            return False
        finally:
            connection.close()
    return True


def child(root: Path) -> None:
    preview.assert_private(root)
    if Path.home().resolve() != (root / "home").resolve():
        raise ValueError("synthetic HOME required")
    server = preview.make_server(root)
    port_file = root / "preview-port"
    try:
        preview.save(port_file, str(server.server_port).encode())
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


def start_candidate(name: str, root: Path) -> None:
    if not units.safe_unit(name):
        raise ValueError("invalid stage unit")
    env = units.command_env()
    args = ["systemd-run", "--user", "--collect", "--quiet",
            "--unit=" + name, "--property=Type=exec",
            "--property=WorkingDirectory=" + str(root),
            "--setenv=HOME=" + str(root / "home"),
            "--setenv=PYTHONPATH=" + os.pathsep.join((
                str(root / "bin"), str(builder.HERE / "src/lib/bob"))),
            "--setenv=PYTHONDONTWRITEBYTECODE=1",
            "--setenv=BOB_MANAGER_BIND=127.0.0.1",
            "--setenv=BOB_MANAGER_PORT=0",
            sys.executable, str(Path(__file__).resolve()),
            "--child-preview-root", str(root)]
    result = subprocess.run(args, capture_output=True, text=True, timeout=12,
                            check=False, env=env)
    if result.returncode:
        raise ValueError("candidate transient unit rejected")


def wait_candidate(root: Path) -> bool:
    for _ in range(15):
        port = port_ready(root / "preview-port")
        if port is not None and preview_probe(port):
            return True
        time.sleep(0.2)
    return False


def stop_unit(name: str) -> None:
    if not units.safe_unit(name):
        raise ValueError("unsafe unit")
    result = units.systemctl("stop", name)
    if result.returncode:
        raise RuntimeError("transient unit cleanup refused")


def execute(scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError("invalid scenario")
    if os.geteuid() == 0:
        raise ValueError("root refused")
    name = units.UNIT_PREFIX + secrets.token_hex(6) + ".service"
    units.absent(name)
    with tempfile.TemporaryDirectory(prefix="bob-v071-preview-") as folder:
        root = Path(folder)
        preview.prepare(root)
        # Preview's two checked files reside under root/bin. They never
        # replace installed binaries and are revalidated before starting.
        preview.assert_private(root)
        launched = False
        try:
            start_candidate(name, root)
            launched = True
            healthy = wait_candidate(root)
            if not healthy:
                raise ValueError("candidate preview HTTP refused")
            service = units.systemctl("show", name, "--property=ActiveState", "--no-pager")
            if service.returncode or service.stdout.strip() != "ActiveState=active":
                raise ValueError("candidate user unit inactive")
            if scenario == "healthy":
                return {"outcome": "candidate_healthy", "real_candidate_http": True,
                        "candidate_files_verified": True, "rollback": "not_needed"}
            # Inject a health verdict failure AFTER verifying real HTTP, so the
            # rollback branch is exercised without damaging actual application.
            return {"outcome": "health_failure_injected", "real_candidate_http": True,
                    "candidate_files_verified": True, "rollback": "needs_recovery_fixture"}
        finally:
            # Even if start reports failure, try to stop the unique unit.
            stop_unit(name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-transient", action="store_true")
    parser.add_argument("--scenario", choices=SCENARIOS, default="healthy")
    parser.add_argument("--child-preview-root", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child_preview_root:
        child(args.child_preview_root)
        return 0
    if not args.execute_transient:
        print("v0.7.1 TWO-FILE SYSTEMD: PLAN ONLY")
        print("Execution needs --execute-transient; no production mode exists.")
        return 0
    try:
        result = execute(args.scenario)
        if args.scenario == "failed-health":
            recovery_name = units.UNIT_PREFIX + secrets.token_hex(6) + ".service"
            units.absent(recovery_name)
            port = units.choose_port()
            started = False
            try:
                cmd = ["systemd-run", "--user", "--collect", "--quiet",
                       "--unit=" + recovery_name, "--property=Type=exec",
                       sys.executable, str(Path(units.__file__).resolve()),
                       "--fixture-port", str(port)]
                response = subprocess.run(cmd, capture_output=True, text=True,
                                          timeout=12, check=False, env=units.command_env())
                if response.returncode:
                    raise ValueError("recovery unit start refused")
                started = True
                recovered = False
                for _ in range(12):
                    if units.probe(port):
                        recovered = True
                        break
                    time.sleep(0.2)
                if not recovered:
                    raise ValueError("recovery health failed")
                result["outcome"] = "synthetic_recovery_healthy"
                result["rollback"] = "candidate_stopped_and_fixture_verified"
            finally:
                # A failed systemd-run may still have registered a unit.
                stop_unit(recovery_name)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            sqlite3.Error) as exc:
        print("v0.7.1 TWO-FILE SYSTEMD: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 TWO-FILE SYSTEMD: PASS")
    for key, value in result.items():
        print(key + ":", value)
    print("Disposable candidate unit stopped. Production Bob untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
