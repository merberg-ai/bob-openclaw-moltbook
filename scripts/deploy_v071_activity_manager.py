#!/usr/bin/env python3
"""v0.7.1 production deployment executor. Explicit approval token REQUIRED.

Not invoked by tests or other scripts. Deploys the two code files only and
performs rollback of code only if restart/health fails. Never changes SQLite.
An interrupted journal requires operator recovery, not blind redeployment.
"""
from __future__ import annotations
import argparse
import base64
from contextlib import closing
import fcntl
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import inspect_package
import plan_v071_production_deployment as planner
import rehearse_v071_regular_file_installer as lab

CONFIRM = "DEPLOY-BOB-V071"
STATE = Path.home() / ".local/state/bob-v071-deploy"
MANAGER = Path.home() / ".local/bin/bob-activity-manager"
NAV = MANAGER.parent / "navigation_shell.py"
JOURNAL = STATE / "transaction.json"
PENDING = STATE / ".transaction-pending"
UNIT = "bob-activity-manager.service"
STATES = ("prepared", "navigation_installed", "manager_installed",
          "restart_requested", "health_failed", "rollback_started",
          "recovery_requested", "complete", "incident")
BASE = builder.PINNED_BASELINE_SHA256


def sha(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("unsafe file")
    return builder.sha256(path.read_bytes())


def secure_dir(path):
    if path.is_symlink():
        raise ValueError("directory symlink")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    s = path.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o077:
        raise ValueError("unsafe state directory")


def save_once(path, data, mode):
    if path.is_symlink() or path.exists():
        raise ValueError("file already exists")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
    finally:
        lab.fsync_dir(path.parent)


def write_journal(phase):
    if phase not in STATES:
        raise ValueError("unsupported journal phase")
    if PENDING.exists() or PENDING.is_symlink():
        raise ValueError("stale pending journal")
    save_once(PENDING, json.dumps({"format": "bob-v071-prod-v1",
                                   "phase": phase, "baseline": BASE},
                                  sort_keys=True).encode(), 0o600)
    os.replace(PENDING, JOURNAL)
    lab.fsync_dir(STATE)


def read_journal():
    if JOURNAL.is_symlink():
        raise ValueError("unsafe journal")
    if not JOURNAL.exists():
        return None
    if not JOURNAL.is_file() or JOURNAL.stat().st_size > 1024:
        raise ValueError("bad journal file")
    obj = json.loads(JOURNAL.read_text())
    if (set(obj) != {"format", "phase", "baseline"}
            or obj["format"] != "bob-v071-prod-v1"
            or obj["phase"] not in STATES or obj["baseline"] != BASE):
        raise ValueError("unexpected journal")
    return obj


def service(action):
    if action not in ("restart",):
        raise ValueError("unsupported systemctl action")
    env = {"PATH": "/usr/bin:/bin", "LANG": "C"}
    for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
        if key in os.environ:
            env[key] = os.environ[key]
    result = subprocess.run(["systemctl", "--user", action, UNIT],
                            capture_output=True, text=True, env=env,
                            timeout=20, check=False)
    if result.returncode:
        raise RuntimeError("service_restart_refused")


def authenticate():
    file = Path.home() / ".config/bob-system/lan-auth.json"
    if file.is_symlink() or not file.is_file() or file.stat().st_uid != os.getuid():
        raise ValueError("auth credential unavailable")
    if stat.S_IMODE(file.stat().st_mode) & 0o077:
        raise ValueError("auth credential not private")
    creds = json.loads(file.read_text())
    if not all(isinstance(creds.get(k), str) and creds[k] for k in ("username", "password")):
        raise ValueError("invalid auth credentials")
    token = base64.b64encode((creds["username"] + ":" + creds["password"]).encode()).decode()
    return "Basic " + token


def probe(authorization, *, candidate):
    for route in ("/healthz", "/", "/activity", "/originals"):
        conn = HTTPConnection("127.0.0.1", 18790, timeout=2)
        try:
            conn.request("GET", route, headers={
                "Host": "127.0.0.1:18790", "Authorization": authorization})
            response = conn.getresponse()
            body = response.read(256 * 1024)
            if response.status != 200:
                return False
            if route == "/healthz":
                if json.loads(body).get("ok") is not True:
                    return False
            elif b"<html" not in body.lower():
                return False
            if candidate and route != "/healthz" and b"bob-layout" not in body:
                return False
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        finally:
            conn.close()
    return True


def bounded_probe(auth, *, candidate):
    for _ in range(10):
        if probe(auth, candidate=candidate):
            return True
        time.sleep(0.5)
    return False


def install(backup):
    # Only one transaction may exist. This must be a single-operator action.
    secure_dir(STATE)
    lock = os.open(STATE / "transaction.lock",
                   os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if read_journal() is not None:
            raise ValueError("previous deployment journal exists; operator review required")
        approval = planner.plan(backup)
        if not approval["ready_for_separate_deployment_review"]:
            raise ValueError("read-only preflight refused")
        if NAV.exists() or NAV.is_symlink() or sha(MANAGER) != BASE:
            raise ValueError("installed code drift or existing nav")
        auth = authenticate()
        if not bounded_probe(auth, candidate=False):
            raise ValueError("existing authenticated HTTP unhealthy")
        candidate, navigation = builder.build()
        inspect_package(builder.review_zip(candidate, navigation))
        original = MANAGER.read_bytes()
        save_once(STATE / "baseline-manager", original, 0o600)
        save_once(STATE / "candidate-manager", candidate, 0o600)
        save_once(STATE / "candidate-navigation", navigation, 0o600)
        write_journal("prepared")
        # File operations can leave a mixed state on interruption. The journal
        # remains for explicit operator-guided recovery in that situation.
        try:
            lab.replace_file(NAV, navigation, None, 0o600)
            write_journal("navigation_installed")
            lab.replace_file(MANAGER, candidate, BASE, 0o700)
            write_journal("manager_installed")
            service("restart")
            write_journal("restart_requested")
            if not bounded_probe(auth, candidate=True):
                raise RuntimeError("candidate_unhealthy")
            write_journal("complete")
            return "candidate_healthy"
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            # If the installed bytes are unexpected, halt rather than overwrite.
            write_journal("health_failed")
            if sha(MANAGER) not in (BASE, builder.sha256(candidate)):
                write_journal("incident")
                raise RuntimeError("installed code changed; manual recovery required")
            if NAV.exists() and sha(NAV) != builder.sha256(navigation):
                write_journal("incident")
                raise RuntimeError("navigation changed; manual recovery required")
            write_journal("rollback_started")
            if sha(MANAGER) != BASE:
                lab.replace_file(MANAGER, original, builder.sha256(candidate), 0o700)
            if NAV.exists():
                NAV.unlink()
                lab.fsync_dir(NAV.parent)
            write_journal("recovery_requested")
            try:
                service("restart")
                if not bounded_probe(auth, candidate=False):
                    raise RuntimeError("baseline_unhealthy")
                write_journal("complete")
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                write_journal("incident")
                raise RuntimeError("baseline_recovery_refused") from None
            return "rolled_back"
    finally:
        os.close(lock)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backup", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm", default="")
    args = p.parse_args()
    if os.geteuid() == 0:
        p.error("refusing root")
    if not args.apply:
        print("v0.7.1 DEPLOY EXECUTOR: PLAN ONLY")
        print("Use v071_release_gate.py to inspect release readiness.")
        print("No service restart or code change.")
        return 0
    if args.confirm != CONFIRM:
        print("v0.7.1 DEPLOY EXECUTOR: REFUSED; explicit confirmation required")
        return 1
    try:
        outcome = install(args.backup)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("v0.7.1 DEPLOY EXECUTOR: REFUSED", type(exc).__name__)
        print("Inspect private transaction journal before any retry.")
        return 1
    print("v0.7.1 DEPLOY EXECUTOR:", outcome)
    print("SQLite data not rolled back or replaced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
