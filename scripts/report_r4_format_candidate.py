#!/usr/bin/env python3
"""R4 format1 signed proposal-only source audit. READ ONLY; no host side effects.

Does not run OpenClaw, install code, change owner controls, touch SQLite,
start/stop services, load credentials or authorize any Moltbook action.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater

PREVIOUS="v0.8.0-r4propose1"
CANDIDATE="v0.8.0-r4format1"
ALLOWED={
    "bob-release-updater":"scripts/bob_release_updater.py",
    "bobctl":"src/bin/bobctl",
    "bob_r4_agent.py":"src/lib/bob/bob_r4_agent.py",
    "bob_r4_installed_gate.py":"src/lib/bob/bob_r4_installed_gate.py",
}


def inspect(root:Path=ROOT)->dict:
    root=Path(root)
    current=root/"releases/current.json"
    offer=root/"releases/candidates/r4-format1-json-reliability.json"
    if current.is_symlink() or offer.is_symlink():
        raise ValueError("r4_format_manifest_symlink")
    active=json.loads(current.read_text(encoding="utf-8"))
    proposed=json.loads(offer.read_text(encoding="utf-8"))
    if (active!=proposed or proposed.get("format")!="bob-updater-v1"
            or proposed.get("release")!=CANDIDATE
            or proposed.get("from")!=PREVIOUS
            or proposed.get("restart_manager") is not True
            or not isinstance(proposed.get("notes"),str)
            or len(proposed["notes"])>800
            or not isinstance(proposed.get("files"),list)
            or len(proposed["files"])!=4):
        raise ValueError("r4_format_exact_offer_unverified")
    digests={}
    for item in proposed["files"]:
        if (not isinstance(item,dict) or set(item)!={"name","source"}
                or item.get("name") not in ALLOWED
                or item.get("source")!=ALLOWED[item["name"]]
                or item["name"] in digests):
            raise ValueError("r4_format_file_scope_unreviewed")
        digests[item["name"]]=hashlib.sha256(
            updater.release_bytes(root,item)).hexdigest()
    if set(digests)!=set(ALLOWED):
        raise ValueError("r4_format_missing_signed_file")

    agent=(root/ALLOWED["bob_r4_agent.py"]).read_text("utf-8")
    gate=(root/ALLOWED["bob_r4_installed_gate.py"]).read_text("utf-8")
    install=(root/ALLOWED["bob-release-updater"]).read_text("utf-8")
    ctl=(root/ALLOWED["bobctl"]).read_text("utf-8")
    transport=(root/"src/bob_v08/shadow.py").read_text("utf-8")
    publisher=(root/"src/bin/bob-moltbook-publisher").read_text("utf-8")
    adapter=(root/"src/lib/bob/bob_r4_publisher_adapter.py").read_text("utf-8")
    outbox=(root/"src/lib/bob/bob_r4_outbox.py").read_text("utf-8")
    controls=(root/"src/lib/bob/bob_r4_controls.py").read_text("utf-8")
    if (not all(marker in agent for marker in (
            "import secrets", "secrets.token_hex(8)",
            '"moltbook-v08-shadow-r4-proposal-"+observed.run_id',
            '"\\nEND_UNTRUSTED_MOLTBOOK_JSON\\n"',
            "TRUSTED OUTPUT CONTRACT", "FINAL ANSWER: SINGLE JSON OBJECT ONLY",
            "decision=parse(raw,observed,now=now",
            "r4_model_selected_disabled_action",
        ))
            or 'session_key.startswith("moltbook-v08-shadow-")' not in transport
            or '["openclaw", "agent", "--agent", "main",' not in transport
            or '"v0.8.0-r4format1": "https"' not in install
            or '"v0.8.0-r4format1": "https"' not in ctl
            or "def preflight_r4_format_patch()" not in install
            or 'not preflight_r4_format_patch()' not in install
            or '"v0.8.0-r4format1":"v0.8.0-r4propose1"' not in install
            or 'FORMAT_RELEASE="v0.8.0-r4format1"' not in gate):
        raise ValueError("r4_format_prompt_transport_or_rollback_unverified")
    for text,marker in (
        (publisher,"R4_SINGLE_PUBLISHER_COMPILED_OFF = True"),
        (adapter,"R4_REAL_DISPATCH_COMPILED_OFF=True"),
        (adapter,"R4_EXACT_OWNER_SEND_COMPILED_OFF=True"),
        (outbox,"PUBLIC_DISPATCH_COMPILED_OFF=True"),
        (controls,"AUTO_ENGINE_COMPILED_OFF=True"),
    ):
        if marker not in text:
            raise ValueError("r4_format_social_send_not_hard_off")

    return {
        "format":"r4-format1-source-review-v1",
        "previous_installed_release":PREVIOUS,
        "candidate_release":CANDIDATE,
        "exact_promoted_candidate":True,
        "candidate_files":len(digests),
        "strict_r4_parser_preserved":True,
        "one_fresh_session_per_requested_decision":True,
        "trusted_json_only_prompt":True,
        "same_openclaw_main_agent_transport":True,
        "all_r4_public_sends_hard_off":True,
        "proposal_schedule_enabled":False,
        "automatic_model_retry_enabled":False,
        "owner_modes_edited":False,
        "database_migrated":False,
        "installed_on_omen":False,
        "source_sha256":digests,
    }


def main(argv=None)->int:
    args=sys.argv[1:] if argv is None else argv
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r4_format_candidate.py --check")
        return 2
    try:
        data=inspect()
    except (OSError,ValueError,TypeError,KeyError,ImportError,UnicodeError):
        print("R4 FORMAT PATCH: REFUSED")
        return 1
    print(json.dumps({k:v for k,v in data.items() if k!="source_sha256"},
                     sort_keys=True,separators=(",",":")))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
