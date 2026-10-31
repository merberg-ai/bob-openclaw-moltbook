#!/usr/bin/env python3
"""CH-HTTPS1 post-install, read-only transport-aware updater acceptance.

Verifies exact installed CH-HTTPS1 release and unchanged Off-first R3 manager,
authenticated loopback HTTP while TLS has NOT been activated, and strict
future TLS mode dispatch. Never opens a public endpoint, reads CA private key,
changes services/database/permissions or calls Moltbook.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src"),str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import r313d_live_off_migration as migration
import report_r313d_host as host
import report_r313d_stage1_installed as stage

RELEASE="v0.8.0-chhttps1"
REQUIRED=frozenset(("bob-release-updater","bobctl","bob-activity-manager",
                    "bob_r3_package.pyz","bob_r313d_owner.py"))


def inspect() -> dict:
    installed=False
    try:
        record=updater.registry()
        installed=(record["release"]==RELEASE
                   and REQUIRED.issubset(record["files"])
                   and updater.live_ok(record))
    except (OSError,ValueError,TypeError,KeyError):
        installed=False
    schema=migration._db_review()
    journal=migration._journal_state()
    try:
        evidence=host.collect(private_copy=False)
        source_off=migration._host_phase_accepted(evidence,schema,journal)
    except (OSError,ValueError,TypeError,KeyError):
        source_off=False
    try:
        mode_ok=(updater.manager_transport(RELEASE)=="http"
                 and updater.manager_transport("v0.8.0-chhttps3")=="https")
    except (OSError,ValueError,TypeError,KeyError):
        mode_ok=False
    if installed and source_off and mode_ok:
        authenticated=("pass" if updater.healthy(
            updater.authorization(),release=RELEASE) else "unverified")
        r3_page=stage._dashboard()
    else:
        authenticated="not_checked"
        r3_page="not_checked"
    passed=(installed and source_off and mode_ok
            and authenticated=="pass"
            and r3_page=="authenticated_read_only_page")
    return {
        "format":"bob-ch-https1-installed-v1",
        "installed_release":"verified" if installed else "not_verified",
        "r3_off_source_gates":"verified" if source_off else "not_verified",
        "r3_schema":schema["state"],
        "migration_journal":journal,
        "current_manager_transport":"http_pre_cutover"
            if mode_ok else "unverified",
        "future_tls_transport":"verified_strict_https"
            if mode_ok else "unverified",
        "authenticated_manager_health":authenticated,
        "authenticated_r3_page":r3_page,
        "installation_acceptance":"PASS" if passed else "NOT_VERIFIED",
        "tls_activated":False,
        "live_services_changed_by_check":False,
        "live_database_changed_by_check":False,
        "new_r3_send_rights":False,
    }


def main(args=None) -> int:
    args=sys.argv[1:] if args is None else args
    if args not in ([],["--json"]):
        print("Usage: python3 scripts/report_ch_https1_installed.py [--json]")
        return 2
    if os.geteuid()==0:
        print("CH-HTTPS1 installed verification refuses root")
        return 1
    report=inspect()
    if args==["--json"]:
        print(json.dumps(report,sort_keys=True,indent=2))
    else:
        print("CH-HTTPS1 TRANSPORT-AWARE UPDATE (READ ONLY)")
        for key in ("installed_release","r3_off_source_gates","r3_schema",
                    "migration_journal","current_manager_transport",
                    "future_tls_transport","authenticated_manager_health",
                    "authenticated_r3_page","installation_acceptance"):
            print(key.replace("_"," ")+":",report[key])
        print("Current LAN HTTP encrypted: NO")
        print("TLS listener enabled: NO")
        print("live services/database changed by check: NO")
        print("new R3 real posting rights: NONE")
    return 0 if report["installation_acceptance"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
