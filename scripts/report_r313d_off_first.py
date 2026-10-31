#!/usr/bin/env python3
"""Read-only owner review for R3.13d Off-first production-code candidate.

No migration, file installation, service action, API request or owner consent.
Reuses the already OMEN-accepted R3.13d host/Off-source attestation and
deterministically builds the proposed package and manager in memory.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src"/"lib"/"bob"),
              str(ROOT/"scripts")]
import build_r313d_manager_candidate
import build_r313d_off_package
import report_r313d_host
from bob_v08.r313d_staging import source_off_gate

CANDIDATE=ROOT/"releases/candidates/r313d-off-first-owner-controls.json"
CURRENT=ROOT/"releases/current.json"
NAMES=(
    "bob_r3_package.pyz","bob-r3-propose","bob_r313d_package.py",
    "bob_r313d_owner.py","bob_r313d_web.py",
    "bob-activity-manager","navigation_shell.py",
)


def review(*, host=True) -> dict:
    try:
        manifest=json.loads(CANDIDATE.read_text("utf-8"))
        live=json.loads(CURRENT.read_text("utf-8"))
        names=tuple(row["name"] for row in manifest["files"])
        if (manifest["format"]!="bob-updater-v1" or
                manifest["release"]!="v0.8.0-r3stage1" or
                manifest["from"]!="v0.8.0-shadow4" or
                live["release"]!="v0.8.0-shadow4" or
                set(names)!=set(NAMES) or len(names)!=len(NAMES) or
                manifest["restart_manager"] is not True or
                any(item["name"]=="bob-moltbook-publisher"
                    for item in manifest["files"])):
            raise ValueError("untrusted_r3_stage_manifest")
        package,launcher=build_r313d_off_package.build()
        manager,nav=build_r313d_manager_candidate.build()
        if (not all(0 < len(x) < 512*1024
                    for x in (package,launcher,manager,nav))
                or b"class Handler(R3HandlerMixin, _LegacyHandler):" not in manager
                or b"/r3" not in nav):
            raise ValueError("r3_stage_build_unverified")
        gate=source_off_gate(ROOT)
        if not gate["production_off_source"]:
            raise ValueError("r3_dispatch_not_compiled_off")
        checkout="PASS"
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,
            ImportError,SyntaxError,json.JSONDecodeError):
        checkout="REFUSED"
    host_report=None
    if host:
        try:
            host_report=report_r313d_host.collect(private_copy=False)
        except (OSError,ValueError,RuntimeError,TypeError):
            host_report=None
    ready = (
        checkout=="PASS" and
        isinstance(host_report,dict) and
        host_report["eligible_for_private_stage"] is True
        and host_report["publisher"]["updater_registry"]=="verified_registry_hash"
        and host_report["host"]["r3_settings"] in ("absent_off","explicit_off")
    ) if host else False
    return {
        "candidate":"v0.8.0-r3stage1",
        "candidate_build":checkout,
        "existing_release":"v0.8.0-shadow4",
        "source_r3_dispatch_off":checkout=="PASS",
        "host_boundary":"eligible" if ready else "review_required",
        "eligible_for_separate_owner_install_review":ready,
        "new_moltbook_dispatch_authorized":False,
        "production_schema_changed":False,
        "installed_code_changed":False,
        "release_manifest_changed":False,
        "canary_authorized":False,
    }


def main(argv=None) -> int:
    opts=sys.argv[1:] if argv is None else argv
    if opts not in ([],["--json"]):
        print("Usage: python3 scripts/report_r313d_off_first.py [--json]")
        return 2
    if os.geteuid()==0:
        print("R3 OFF-FIRST REVIEW: refuse root")
        return 1
    result=review()
    if "--json" in opts:
        print(json.dumps(result,sort_keys=True,indent=2))
    else:
        print("R3.13d OFF-FIRST OWNER CODE RELEASE (read only)")
        print("candidate build: "+result["candidate_build"])
        print("existing release: "+result["existing_release"])
        print("three R3 real-send gates: "+(
            "OFF" if result["source_r3_dispatch_off"] else "unverified"))
        print("installed host boundary: "+result["host_boundary"])
        print("eligible for separate owner install review: "+(
            "yes" if result["eligible_for_separate_owner_install_review"]
            else "no"))
        print("live database or services changed: NO")
        print("real Bob-authored publication rights: NONE")
        print("real Moltbook canary authorized: NO")
    return 0 if result["eligible_for_separate_owner_install_review"] else 1


if __name__=="__main__":
    raise SystemExit(main())
