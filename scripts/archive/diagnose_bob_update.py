#!/usr/bin/env python3
"""Read-only diagnosis for a refused bobctl update.

Prints only check names / safe statuses. Does not acquire a write lock, make
backups, install/restart code, write SQLite, expose auth, or submit Moltbook
requests. Uses authenticated local GETs to diagnose strict health probes.
"""
from __future__ import annotations

from http.client import HTTPConnection
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys

import bob_release_updater as updater

ROUTES = ("/healthz", "/settings", "/activity", "/system/status", "/api/system/status")


def show(name, result, explanation=""):
    print(f"{name}: {result}" + (f" ({explanation})" if explanation else ""))


def main():
    print("BOB UPDATER DIAGNOSIS (READ-ONLY; no service / database changes)")
    checks_failed = 0

    def check(name, action):
        nonlocal checks_failed
        try:
            outcome = action()
            if outcome is False:
                show(name, "FAIL")
                checks_failed += 1
            else:
                show(name, "PASS")
            return outcome
        except (OSError, ValueError, RuntimeError, sqlite3.Error,
                KeyError, TypeError, AttributeError) as exc:
            show(name, "FAIL", type(exc).__name__)
            checks_failed += 1
            return None

    folder = check("trusted_main_checkout", updater.checkout_from_config)
    if folder is None:
        print("STOP: trusted main checkout check failed; do not rerun update")
        return 1
    current = check("private_installed_registry", updater.registry)
    plan = check("release_manifest", lambda: updater.manifest(folder))
    if current is None or plan is None:
        print("STOP: updater state/manifest could not be read")
        return 1
    show("installed_release", current["release"])
    show("available_release", plan["release"])
    check("release_chain", lambda: plan["from"] == current["release"])
    check("registered_live_code_hashes", lambda: updater.live_ok(current))

    journal = check("private_transaction_journal", updater.read_journal)
    if journal:
        show("transaction_phase", str(journal.get("phase", "unknown")))
        if journal.get("phase") not in ("complete", "rolled_back"):
            show("stop_condition", "INCOMPLETE TRANSACTION; do not retry")
            checks_failed += 1
    else:
        show("transaction_phase", "absent")
    tx = updater.STATE_DIR / ("tx-" + plan["release"])
    check("release_archive_path_type", lambda: not tx.is_symlink())
    show("release_archive_exists", "YES" if tx.exists() else "NO")
    if tx.exists():
        show("stop_condition", "RELEASE ARCHIVE EXISTS; updater refuses reuse")
        checks_failed += 1

    backup = updater.BACKUP_DIR
    if backup.is_symlink():
        show("backup_directory", "FAIL", "symlink")
        checks_failed += 1
    elif backup.exists():
        s = backup.stat()
        check("backup_directory", lambda: stat.S_ISDIR(s.st_mode)
              and not (stat.S_IMODE(s.st_mode) & 0o077))
    else:
        show("backup_directory", "NOT CREATED (backup utility may create it)")
    check("live_database_present", lambda: updater.DB.is_file()
          and not updater.DB.is_symlink())

    # Inspect route availability without disclosing password or response body.
    auth = check("private_dashboard_credentials", updater.authorization)
    if auth is not None:
        for route in ROUTES:
            def route_check():
                conn = HTTPConnection("127.0.0.1", 18790, timeout=17 if "status" in route else 6)
                try:
                    conn.request("GET", route, headers={
                        "Host": "127.0.0.1:18790", "Authorization": auth})
                    response = conn.getresponse()
                    raw = response.read(262145)
                    if response.status != 200 or len(raw) > 262144:
                        return False
                    if route == "/healthz":
                        return json.loads(raw).get("ok") is True
                    if route == "/api/system/status":
                        return isinstance(json.loads(raw).get("services"), list)
                    return True
                finally:
                    conn.close()
            check("authenticated_GET " + route, route_check)
    print("Summary:", checks_failed, "failure/stop condition(s)")
    print("No changes made. Do not run update/recover based on this report alone.")
    return 1 if checks_failed else 0


if __name__ == "__main__":
    sys.exit(main())
