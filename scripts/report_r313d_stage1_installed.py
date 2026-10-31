#!/usr/bin/env python3
"""Post-install read-only R3.13d Off-first acceptance.

This verifies the already operator-installed stage1 package and the running
authenticated LAN dashboard. NO publisher changes, no SQLite writes,
no model run, no Moltbook credentials or API calls, and no R3 posting consent.
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
from http.client import HTTPConnection

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src"),
             str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import report_r313d_host as prior
import r313d_live_off_migration as migration

RELEASE="v0.8.0-r3stage1"
REQUIRED=frozenset((
    "bob_r3_package.pyz","bob-r3-propose",
    "bob_r313d_package.py","bob_r313d_owner.py",
    "bob_r313d_web.py","bob-activity-manager",
    "navigation_shell.py",
))
HOST="127.0.0.1"
PORT=18790


def _dashboard() -> str:
    """Require an authenticated actual R3 GET; tolerate brief manager startup.

    Every probe is localhost, GET-only and bounded; never print credentials,
    response bodies, private post text or exception details. A non-200, missing
    compiled-Off label or persistent network error still fails closed.
    """
    try:
        auth = updater.authorization()
    except (OSError, ValueError, KeyError, TypeError):
        return "unverified"
    for attempt in range(3):
        try:
            client = HTTPConnection(HOST, PORT, timeout=8)
            try:
                client.request("GET", "/r3", headers={
                    "Host": "127.0.0.1:18790",
                    "Authorization": auth,
                })
                response = client.getresponse()
                page = response.read(65537)
                if (response.status == 200 and len(page) <= 65536
                        and b"Bob R3 Controls" in page
                        and b"R3 automatic publishing" in page
                        and b"compiled locked" in page
                        and b"Owner controls remain unavailable" not in page):
                    return "authenticated_read_only_page"
            finally:
                client.close()
        except (OSError, ValueError, KeyError, TimeoutError):
            pass
        if attempt < 2:
            time.sleep(0.4)
    return "unverified"


def inspect() -> dict:
    try:
        registry=updater.registry()
        install=(
            registry["release"]==RELEASE
            and REQUIRED.issubset(registry["files"])
            and updater.live_ok(registry))
    except (OSError,ValueError,KeyError,TypeError):
        install=False
    schema = migration._db_review()
    journal = migration._journal_state()
    try:
        host = prior.collect(private_copy=False)
        host_off = migration._host_phase_accepted(host, schema, journal)
    except (OSError, ValueError, KeyError, TypeError):
        host_off = False
    ui = _dashboard() if install and host_off else "not_checked"
    return {
        "format":"bob-r313d-off-first-installed-v1",
        "off_first_release":"verified" if install else "not_verified",
        "r3_send_guards":"verified_off" if host_off else "unverified",
        "owner_controls_ui":ui,
        "r3_schema":schema["state"],
        "migration_journal":journal,
        "installed_acceptance":bool(
            install and host_off and ui=="authenticated_read_only_page"),
        "live_schema_modified_by_check":False,
        "services_changed_by_check":False,
        "new_r3_publication_rights":False,
        "moltbook_api_calls":0,
        "manual_canary_authorized":False,
    }


def main(args=None) -> int:
    args=sys.argv[1:] if args is None else args
    if args not in ([],["--json"]):
        print("Usage: python3 scripts/report_r313d_stage1_installed.py [--json]")
        return 2
    if os.geteuid()==0:
        print("R3.13d stage1 acceptance refuses root")
        return 1
    data=inspect()
    if "--json" in args:
        print(json.dumps(data,sort_keys=True,indent=2))
    else:
        print("R3.13d OFF-FIRST STAGE1 INSTALLED (READ-ONLY)")
        print("installed release:",data["off_first_release"])
        print("R3 real-send source gates:",data["r3_send_guards"])
        print("authenticated R3 Controls:",data["owner_controls_ui"])
        print("R3 schema:",data["r3_schema"])
        print("migration journal:",data["migration_journal"])
        print("installation acceptance:","PASS" if data[
            "installed_acceptance"] else "NOT VERIFIED")
        print("live database or services changed by check: NO")
        print("new public R3 posting rights: NONE")
        print("Moltbook canary authorized: NO")
    return 0 if data["installed_acceptance"] else 1


if __name__=="__main__":
    raise SystemExit(main())
