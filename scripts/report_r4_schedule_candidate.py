#!/usr/bin/env python3
"""R4 schedule1 OFF-first signed release source audit (READ ONLY).

Never installs a unit, starts a timer, invokes OpenClaw, writes a database,
changes a mode, changes a publisher or contacts the Moltbook API.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater

PREVIOUS="v0.8.0-r4format1"
RELEASE="v0.8.0-r4schedule1"
ALLOWED={
    "bob-release-updater":"scripts/bob_release_updater.py",
    "bobctl":"src/bin/bobctl",
    "bob_r4_installed_gate.py":"src/lib/bob/bob_r4_installed_gate.py",
    "bob_r4_schedule.py":"src/lib/bob/bob_r4_schedule.py",
    "bob-r4-schedule":"src/bin/bob-r4-schedule",
    "bob_r4_web.py":"src/lib/bob/bob_r4_web.py",
}


def inspect(root:Path=ROOT)->dict:
    root=Path(root)
    current=root/"releases/current.json"
    candidate=root/"releases/candidates/r4-schedule1-offfirst.json"
    if current.is_symlink() or candidate.is_symlink():
        raise ValueError("r4_schedule_candidate_symlink")
    live=json.loads(current.read_text(encoding="utf-8"))
    reviewed=json.loads(candidate.read_text(encoding="utf-8"))
    if (live!=reviewed or type(live) is not dict or
            set(live)!={"format","release","from","notes",
                        "files","restart_manager"}
            or live.get("format")!="bob-updater-v1"
            or live.get("release")!=RELEASE
            or live.get("from")!=PREVIOUS
            or live.get("restart_manager") is not True
            or type(live.get("notes")) is not str
            or len(live["notes"])>800
            or type(live.get("files")) is not list
            or len(live["files"])!=len(ALLOWED)):
        raise ValueError("r4_schedule_exact_release_unverified")
    digests={}
    for row in live["files"]:
        if (type(row) is not dict or set(row)!={"name","source"}
                or row.get("name") not in ALLOWED
                or row.get("source")!=ALLOWED[row["name"]]
                or row["name"] in digests):
            raise ValueError("r4_schedule_file_scope_unreviewed")
        digests[row["name"]]=hashlib.sha256(
            updater.release_bytes(root,row)).hexdigest()
    if set(digests)!=set(ALLOWED):
        raise ValueError("r4_schedule_signed_files_missing")

    schedule=(root/ALLOWED["bob_r4_schedule.py"]).read_text("utf-8")
    entry=(root/ALLOWED["bob-r4-schedule"]).read_text("utf-8")
    gate=(root/ALLOWED["bob_r4_installed_gate.py"]).read_text("utf-8")
    controller=(root/ALLOWED["bobctl"]).read_text("utf-8")
    installer=(root/ALLOWED["bob-release-updater"]).read_text("utf-8")
    view=(root/ALLOWED["bob_r4_web.py"]).read_text("utf-8")
    adapter=(root/"src/lib/bob/bob_r4_publisher_adapter.py").read_text("utf-8")
    publisher=(root/"src/bin/bob-moltbook-publisher").read_text("utf-8")
    outbox=(root/"src/lib/bob/bob_r4_outbox.py").read_text("utf-8")
    controls=(root/"src/lib/bob/bob_r4_controls.py").read_text("utf-8")
    agent=(root/"src/lib/bob/bob_r4_agent.py").read_text("utf-8")

    contract={
        "schedule":(
            'SERVICE="bob-r4-propose.service"',
            'TIMER="bob-r4-propose.timer"',
            'OnActiveSec=120min','OnUnitInactiveSec=120min',
            'RandomizedDelaySec=10min','Persistent=false',
            'ExecStart=%h/.local/bin/bob-r4-schedule --once',
            'def _signed()->bool:', 'def stage(', 'def enable(',
            'def disable(', 'def recover(', 'def once(',
            'def _other_workers_idle(', 'def _owner_modes_ready(',
            'from bob_r4_producer import run_one',
            'r4_schedule_guard_refused',
            'Type "+phrase+" to apply reviewed R4-only change',
        ),
        "entry":('from bob_r4_schedule import main as schedule_main',),
        "gate":('SCHEDULE_RELEASE="v0.8.0-r4schedule1"',
                '"bob-r4-schedule","bob_r4_schedule.py"'),
        "controller":('"v0.8.0-r4schedule1": "https"',),
        "updater":('"v0.8.0-r4schedule1": "https"',
                   "def preflight_r4_schedule_patch()",
                   'not preflight_r4_schedule_patch()',
                   'r4_schedule_units_absent()',
                   '"v0.8.0-r4schedule1":"v0.8.0-r4format1"'),
        "web":('def _schedule_status(data):',
               'from bob_r4_schedule import inspect as schedule_inspect'),
        "agent":("secrets.token_hex(8)","TRUSTED OUTPUT CONTRACT"),
    }
    values={"schedule":schedule,"entry":entry,"gate":gate,
            "controller":controller,"updater":installer,
            "web":view,"agent":agent}
    if any(marker not in values[name] for name,names in contract.items()
           for marker in names):
        raise ValueError("r4_schedule_exact_signed_source_drift")
    for body,needle in (
        (publisher,"R4_SINGLE_PUBLISHER_COMPILED_OFF = True"),
        (adapter,"R4_REAL_DISPATCH_COMPILED_OFF=True"),
        (adapter,"R4_EXACT_OWNER_SEND_COMPILED_OFF=True"),
        (outbox,"PUBLIC_DISPATCH_COMPILED_OFF=True"),
        (controls,"AUTO_ENGINE_COMPILED_OFF=True"),
    ):
        if needle not in body:
            raise ValueError("r4_schedule_public_send_gate_drift")

    if ("subprocess"+"."+"run([" in schedule and
            '["systemctl","--user",*args]' not in schedule):
        raise ValueError("r4_schedule_unbounded_systemd_command")
    return {
        "format":"r4-schedule1-source-review-v1",
        "candidate_release":RELEASE,
        "from_release":PREVIOUS,
        "exact_promoted_candidate":True,
        "signed_candidate_files":len(digests),
        "unit_stage_owner_confirmed_only":True,
        "schedule_enable_owner_confirmed_only":True,
        "schedule_installed_by_updater":False,
        "schedule_enabled_by_updater":False,
        "no_automatic_model_retry":True,
        "existing_r3_publisher_and_scout_unchanged":True,
        "all_r4_public_sends_hard_off":True,
        "no_database_migration":True,
        "authenticated_https":True,
        "host_installed_by_source_audit":False,
        "verified_sha256":digests,
    }


def main(args=None)->int:
    args=sys.argv[1:] if args is None else args
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r4_schedule_candidate.py --check")
        return 2
    try:
        data=inspect()
    except (OSError,ValueError,TypeError,KeyError,ImportError,
            UnicodeError,RuntimeError):
        print("R4 SCHEDULE SOURCE: REFUSED")
        return 1
    print(json.dumps({k:v for k,v in data.items() if k!="verified_sha256"},
                     sort_keys=True,separators=(",",":")))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
