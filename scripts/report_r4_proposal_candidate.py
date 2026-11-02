#!/usr/bin/env python3
"""Read-only signed R4 proposal-only PATCH source review, no host operations.

R4 "autonomy1" remains current. This check is for an exact FOUR-file FUTURE
candidate and cannot promote, install, run OpenClaw, edit controls or publish.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater

CURRENT="v0.8.0-autonomy1"
PATCH="v0.8.0-r4propose1"
ALLOWED={
    "bob-release-updater":"scripts/bob_release_updater.py",
    "bobctl":"src/bin/bobctl",
    "bob_r4_agent.py":"src/lib/bob/bob_r4_agent.py",
    "bob_r4_installed_gate.py":"src/lib/bob/bob_r4_installed_gate.py",
}


def inspect(root:Path=ROOT)->dict:
    root=Path(root)
    live=root/"releases/current.json"
    patch=root/"releases/candidates/r4-propose1-one-shot.json"
    if live.is_symlink() or patch.is_symlink():
        raise ValueError("r4_patch_manifest_symlink")
    current=json.loads(live.read_text("utf-8"))
    candidate=json.loads(patch.read_text("utf-8"))
    if (current.get("release")!=CURRENT
            or current.get("from")!="v0.8.0-r3canary1"
            or candidate.get("release")!=PATCH
            or candidate.get("from")!=CURRENT
            or candidate.get("format")!="bob-updater-v1"
            or candidate.get("restart_manager") is not True
            or type(candidate.get("files")) is not list
            or len(candidate["files"])!=len(ALLOWED)
            or type(candidate.get("notes")) is not str
            or len(candidate["notes"])>800):
        raise ValueError("r4_proposal_patch_chain_unverified")
    files={}
    for item in candidate["files"]:
        if (not isinstance(item,dict)
                or set(item)!={"name","source"}
                or item.get("name") not in ALLOWED
                or item["name"] in files
                or item["source"]!=ALLOWED[item["name"]]):
            raise ValueError("r4_proposal_patch_scope_unreviewed")
        files[item["name"]]=hashlib.sha256(
            updater.release_bytes(root,item)).hexdigest()
    if set(files)!=set(ALLOWED):
        raise ValueError("r4_proposal_patch_files_missing")
    agent=(root/"src/lib/bob/bob_r4_agent.py").read_text("utf-8")
    upstream=(root/"src/bob_v08/shadow.py").read_text("utf-8")
    updater_code=(root/"scripts/bob_release_updater.py").read_text("utf-8")
    controller=(root/"src/bin/bobctl").read_text("utf-8")
    gate=(root/"src/lib/bob/bob_r4_installed_gate.py").read_text("utf-8")
    publisher=(root/"src/bin/bob-moltbook-publisher").read_text("utf-8")
    adapter=(root/"src/lib/bob/bob_r4_publisher_adapter.py").read_text("utf-8")
    outbox=(root/"src/lib/bob/bob_r4_outbox.py").read_text("utf-8")
    controls=(root/"src/lib/bob/bob_r4_controls.py").read_text("utf-8")
    if ('"moltbook-v08-shadow-r4-proposal-"+observed.run_id' not in agent
            or 'session_key.startswith("moltbook-v08-shadow-")' not in upstream
            or '["openclaw", "agent", "--agent", "main",' not in upstream
            or '"v0.8.0-r4propose1": "https"' not in updater_code
            or '"v0.8.0-r4propose1": "https"' not in controller
            or 'not preflight_r4_proposal_patch()' not in updater_code
            or 'def preflight_r4_proposal_patch()' not in updater_code
            or 'PROPOSAL_RELEASE="v0.8.0-r4propose1"' not in gate
            or 'detail["release"]!=info["release"]' not in gate):
        raise ValueError("r4_proposal_patch_transport_or_attestation_drift")
    for target,needle in (
        (publisher,"R4_SINGLE_PUBLISHER_COMPILED_OFF = True"),
        (adapter,"R4_REAL_DISPATCH_COMPILED_OFF=True"),
        (adapter,"R4_EXACT_OWNER_SEND_COMPILED_OFF=True"),
        (outbox,"PUBLIC_DISPATCH_COMPILED_OFF=True"),
        (controls,"AUTO_ENGINE_COMPILED_OFF=True"),
    ):
        if needle not in target:
            raise ValueError("r4_proposal_patch_public_send_not_hard_off")
    return {
        "format":"r4-propose1-source-review-v1",
        "current_release_unchanged":current["release"],
        "candidate_release":candidate["release"],
        "from_release":candidate["from"],
        "candidate_files":len(files),
        "main_agent_transport_compatible":True,
        "signed_r4_host_patch_preflight_required":True,
        "all_r4_public_sends_hard_off":True,
        "proposal_schedule_enabled":False,
        "owner_modes_edited":False,
        "database_migrated":False,
        "installed_on_omen":False,
        "verified_source_hashes":files,
    }


def main(args=None)->int:
    args=sys.argv[1:] if args is None else args
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r4_proposal_candidate.py --check")
        return 2
    try:
        result=inspect()
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,ImportError):
        print("R4 PROPOSAL PATCH: REFUSED")
        return 1
    print(json.dumps({
        k:v for k,v in result.items() if k!="verified_source_hashes"
    },sort_keys=True,separators=(",",":")))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
