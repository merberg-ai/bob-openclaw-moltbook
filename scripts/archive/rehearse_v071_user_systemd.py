#!/usr/bin/env python3
"""Opt-in disposable user-systemd HTTP staging; NEVER operates on Bob's unit.

Default mode is a read-only plan. --execute-transient explicitly authorizes
starting/stopping a uniquely named temporary user unit with a synthetic fixture.
"""
from __future__ import annotations
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.client import HTTPConnection
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

UNIT_PREFIX = "bob-v071-stage-"
LIVE_UNIT = "bob-activity-manager.service"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"v071-stage-ok" if self.path == "/healthz" else b"not-found"
        self.send_response(200 if self.path == "/healthz" else 404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

def safe_unit(name):
    return (name.startswith(UNIT_PREFIX) and name.endswith(".service")
            and len(name) == len(UNIT_PREFIX) + 12 + len(".service")
            and all(c in "0123456789abcdef" for c in name[len(UNIT_PREFIX):-8])
            and name != LIVE_UNIT)

def command_env():
    result = {"PATH": "/usr/bin:/bin", "LANG": "C"}
    for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
        if key in os.environ:
            result[key] = os.environ[key]
    return result

def systemctl(*args):
    return subprocess.run(["systemctl", "--user", *args], capture_output=True,
                          timeout=8, text=True, env=command_env(), check=False)

def absent(name):
    if not safe_unit(name):
        raise ValueError("invalid synthetic unit")
    result = systemctl("show", name, "--property=LoadState", "--no-pager")
    if result.returncode or result.stdout.strip() != "LoadState=not-found":
        raise ValueError("stage unit already present or cannot prove absence")

def probe(port):
    connection = HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", "/healthz")
        result = connection.getresponse()
        return result.status == 200 and result.read(64) == b"v071-stage-ok"
    except (OSError, TimeoutError):
        return False
    finally:
        connection.close()

def choose_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

def fixture(port):
    if not 1 <= port <= 65535:
        raise ValueError("invalid port")
    server = HTTPServer(("127.0.0.1", port), Handler)
    server.serve_forever(poll_interval=0.1)

def execute():
    if os.geteuid() == 0:
        raise ValueError("refusing root")
    name = UNIT_PREFIX + secrets.token_hex(6) + ".service"
    if not safe_unit(name):
        raise AssertionError("invalid generated unit")
    port = choose_port()
    absent(name)
    with tempfile.TemporaryDirectory(prefix="bob-v071-systemd-") as folder:
        if not Path(folder).is_dir():
            raise ValueError("missing private directory")
        # systemd-run invokes Python with an explicit script, matching Bob's
        # interpreter + script shape, but neither script nor unit is Bob's.
        cmd = ["systemd-run", "--user", "--collect", "--quiet",
               "--unit=" + name, "--property=Type=exec",
               "--property=WorkingDirectory=" + folder,
               sys.executable, str(Path(__file__).resolve()),
               "--fixture-port", str(port)]
        started = False
        try:
            run = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=12, check=False, env=command_env())
            if run.returncode:
                raise ValueError("transient unit start refused")
            started = True
            ok = False
            for _ in range(12):
                if probe(port):
                    ok = True
                    break
                time.sleep(0.2)
            if not ok:
                raise ValueError("synthetic HTTP unhealthy")
            state = systemctl("show", name, "--property=ActiveState", "--no-pager")
            if state.returncode or state.stdout.strip() != "ActiveState=active":
                raise ValueError("synthetic unit not active")
            return {"isolated_http": True, "synthetic_unit_started": True,
                    "live_unit_unchanged_by_script": True}
        finally:
            # Always attempt bounded cleanup, even after a start command failure:
            # systemd-run may have created the unit before reporting an error.
            stop = systemctl("stop", name)
            if started and stop.returncode:
                raise RuntimeError("stage unit cleanup failed; operator review required")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-transient", action="store_true")
    parser.add_argument("--fixture-port", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.fixture_port is not None:
        # Only start synthetic fixture; no access to other service or state.
        fixture(args.fixture_port)
        return 0
    if not args.execute_transient:
        print("v0.7.1 USER SYSTEMD STAGING: PLAN ONLY")
        print("No transient unit created. --execute-transient is explicit opt-in.")
        return 0
    try:
        result = execute()
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print("v0.7.1 USER SYSTEMD STAGING: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 USER SYSTEMD STAGING: PASS")
    for key, value in result.items():
        print(key + ":", value)
    print("Transient unit stopped; production Bob never targeted.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
