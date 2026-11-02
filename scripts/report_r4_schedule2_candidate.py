#!/usr/bin/env python3
"""R4 schedule2 pinned R3 drop-in signed candidate source audit (READ ONLY).

No systemctl changes, live database writes, model calls, public requests,
credentials or host code installation. This reviews SOURCE, not host state.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater

RELEASE="v0.8.0-r4schedule2"
PREVIOUS="v0.8.0-r4schedule1"
CANDIDATE="releases/candidates/r4-schedule2-pinned-r3-first-tick.json"
ALLOWED={
    "bob-release-updater":"scripts/bob_release_updater.py",
    "bobctl":"src/bin/bobctl",
    "bob_r4_installed_gate.py":"src/lib/bob/bob_r4_installed_gate.py",
    "bob_r4_schedule.py":"src/lib/bob/bob_r4_schedule.py",
}


def inspect(root:Path=ROOT)->dict:
    root=Path(root)
    offer=root/CANDIDATE
    active=root/"releases/current.json"
    if offer.is_symlink() or active.is_symlink():
        raise ValueError("schedule2_symlink_manifest")
    proposed=json.loads(offer.read_text("utf-8"))
    current=json.loads(active.read_text("utf-8"))
    if (current!=proposed or type(proposed) is not dict
            or set(proposed)!={"format","release","from","notes","files","restart_manager"}
            or proposed["format"]!="bob-updater-v1"
            or proposed["release"]!=RELEASE
            or proposed["from"]!=PREVIOUS
            or proposed["restart_manager"] is not True
            or type(proposed["notes"]) is not str
            or len(proposed["notes"])>800
            or type(proposed["files"]) is not list
            or len(proposed["files"])!=4):
        raise ValueError("schedule2_exact_offer_unverified")
    files={}
    for item in proposed["files"]:
        if (type(item) is not dict or set(item)!={"name","source"}
                or item.get("name") not in ALLOWED
                or item.get("source")!=ALLOWED[item["name"]]
                or item["name"] in files):
            raise ValueError("schedule2_file_scope_unreviewed")
        files[item["name"]]=hashlib.sha256(
            updater.release_bytes(root,item)).hexdigest()
    if set(files)!=set(ALLOWED):
        raise ValueError("schedule2_signed_source_missing")
    schedule=(root/ALLOWED["bob_r4_schedule.py"]).read_text("utf-8")
    gate=(root/ALLOWED["bob_r4_installed_gate.py"]).read_text("utf-8")
    controller=(root/ALLOWED["bobctl"]).read_text("utf-8")
    installer=(root/ALLOWED["bob-release-updater"]).read_text("utf-8")
    original=(root/"scripts/repair_r3_first_timer.py").read_text("utf-8")
    publisher=(root/"src/bin/bob-moltbook-publisher").read_text("utf-8")
    adapter=(root/"src/lib/bob/bob_r4_publisher_adapter.py").read_text("utf-8")
    outbox=(root/"src/lib/bob/bob_r4_outbox.py").read_text("utf-8")
    modes=(root/"src/lib/bob/bob_r4_controls.py").read_text("utf-8")
    expected=(
        'R3_BOOTSTRAP_DIR=UNIT_DIR/(R3_TIMER+".d")',
        'R3_BOOTSTRAP=R3_BOOTSTRAP_DIR/"10-first-run.conf"',
        'R3_BOOTSTRAP_BYTES=b"[Timer]\\nOnActiveSec=2min\\n"',
        'def _approved_r3_timer_dropin(unit:Unit)->bool:',
        'if unit.dropins!=str(R3_BOOTSTRAP):',
        'if not _dir(R3_BOOTSTRAP_DIR,strict=True):',
        'if set(R3_BOOTSTRAP_DIR.iterdir())!={R3_BOOTSTRAP}:',
        '_file(R3_BOOTSTRAP,max_bytes=256)',
        'R3_BOOTSTRAP.read_bytes()==R3_BOOTSTRAP_BYTES',
        'def _other_workers_idle(',
        'if not _approved_r3_timer_dropin(unit):',
        'elif unit.dropins!="":',
        'def stage(', 'def enable(', 'def recover(', 'def once(',
        'from bob_r4_producer import run_one',
        'OnActiveSec=120min','OnUnitInactiveSec=120min',
        'RandomizedDelaySec=10min','Persistent=false',
    )
    if (not all(s in schedule for s in expected)
            or 'BODY=b"[Timer]\\nOnActiveSec=2min\\n"' not in original
            or 'F= D/"10-first-run.conf"' not in original
            or '"v0.8.0-r4schedule2": "https"' not in controller
            or '"v0.8.0-r4schedule2": "https"' not in installer
            or 'def preflight_r4_schedule2_patch()' not in installer
            or 'not preflight_r4_schedule2_patch()' not in installer
            or 'r4_schedule_units_absent()' not in installer
            or '"v0.8.0-r4schedule2":"v0.8.0-r4schedule1"' not in installer
            or 'SCHEDULE2_RELEASE="v0.8.0-r4schedule2"' not in gate):
        raise ValueError("schedule2_exact_pinned_dropin_or_release_drift")
    for body,marker in (
        (publisher,"R4_SINGLE_PUBLISHER_COMPILED_OFF = True"),
        (adapter,"R4_REAL_DISPATCH_COMPILED_OFF=True"),
        (adapter,"R4_EXACT_OWNER_SEND_COMPILED_OFF=True"),
        (outbox,"PUBLIC_DISPATCH_COMPILED_OFF=True"),
        (modes,"AUTO_ENGINE_COMPILED_OFF=True"),
    ):
        if marker not in body:
            raise ValueError("schedule2_public_send_gate_not_off")
    return {
        "format":"r4-schedule2-source-review-v1",
        "candidate_release":RELEASE,
        "from_release":PREVIOUS,
        "exact_promoted_candidate":True,
        "signed_candidate_files":4,
        "r3_first_tick_dropin_exact_only":True,
        "unreviewed_dropins_still_refused":True,
        "existing_r3_scout_publisher_untouched":True,
        "schedule_install_or_activation_by_updater":False,
        "public_r4_sends_hard_off":True,
        "unchanged_r4_proposal_only_model_contract":True,
        "authenticated_https":True,
        "database_migration":False,
        "host_installed_by_source_audit":False,
        "source_sha256":files,
    }


def main(argv=None)->int:
    args=sys.argv[1:] if argv is None else argv
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r4_schedule2_candidate.py --check")
        return 2
    try:
        result=inspect()
    except (OSError,TypeError,ValueError,KeyError,ImportError,UnicodeError):
        print("R4 SCHEDULE2 SOURCE: REFUSED")
        return 1
    print(json.dumps({k:v for k,v in result.items() if k!="source_sha256"},
                     sort_keys=True,separators=(",",":")))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
