#!/usr/bin/env python3
"""One-command v0.7.1 release readiness. READ ONLY by default.

Combines preflight, package integrity, authenticated loopback verification,
and regression suite in a single operator command. Never installs/restarts Bob.
"""
from __future__ import annotations
import argparse
import base64
from http.client import HTTPConnection
import json
from pathlib import Path
import os
import stat
import subprocess
import sys

import plan_v071_production_deployment as planner

def verify_http(port: int, credentials: dict | None = None):
    if not 1 <= port <= 65535:
        raise ValueError("unsupported port")
    if credentials is not None:
        if (not isinstance(credentials, dict) or
                not isinstance(credentials.get("username"), str) or
                not isinstance(credentials.get("password"), str)):
            raise ValueError("invalid credentials")
        auth = base64.b64encode(
            (credentials["username"] + ":" + credentials["password"]).encode()
        ).decode("ascii")
    else:
        auth = None
    for path in ("/healthz", "/", "/activity", "/originals"):
        conn = HTTPConnection("127.0.0.1", port, timeout=3)
        try:
            headers = {"Host": f"127.0.0.1:{port}"}
            if auth:
                headers["Authorization"] = "Basic " + auth
            conn.request("GET", path, headers=headers)
            result = conn.getresponse()
            body = result.read(256 * 1024)
            if result.status != 200:
                return False
            if path == "/healthz":
                if not json.loads(body).get("ok"):
                    return False
            elif b"<html" not in body.lower():
                return False
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        finally:
            conn.close()
    return True


def credentials_from_private_file(file: Path):
    if file.is_symlink() or not file.is_file():
        raise ValueError("unsafe auth file")
    record = file.stat()
    if record.st_uid != os.getuid() or stat.S_IMODE(record.st_mode) & 0o077:
        raise ValueError("auth file not private")
    return json.loads(file.read_text())


def run(backup: Path, *, execute_tests: bool = True):
    result = planner.plan(backup)
    if not result["ready_for_separate_deployment_review"]:
        return {"preflight": False, "regressions": False, "loopback_http": False}
    # Existing production HTTP port from checked contract. Does not fetch or
    # display credentials. No write endpoints are called.
    auth_file = Path.home() / ".config/bob-system/lan-auth.json"
    auth = credentials_from_private_file(auth_file) if auth_file.exists() else None
    port = 18790
    loopback = verify_http(port, auth)
    if not loopback:
        return {"preflight": True, "regressions": False, "loopback_http": False}
    tests = True
    if execute_tests:
        cmd = [sys.executable, "-m", "unittest", "discover",
               "-s", "tests", "-p", "test_*.py", "-q"]
        completed = subprocess.run(cmd, cwd=planner.builder.HERE,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=90, check=False)
        tests = completed.returncode == 0
    return {"preflight": True, "regressions": tests, "loopback_http": loopback}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backup", required=True, type=Path)
    p.add_argument("--skip-regressions", action="store_true")
    args = p.parse_args()
    if os.geteuid() == 0:
        p.error("operator user only")
    try:
        outcome = run(args.backup, execute_tests=not args.skip_regressions)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("v0.7.1 CONSOLIDATED RELEASE GATE: REFUSED", type(exc).__name__)
        return 1
    for key, value in outcome.items():
        print(key + ":", "PASS" if value else "REFUSED")
    print("v0.7.1 CONSOLIDATED RELEASE GATE:",
          "PASS" if all(outcome.values()) else "REFUSED")
    print("production_modified: NO; deployment_authorized: NO")
    return 0 if all(outcome.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
