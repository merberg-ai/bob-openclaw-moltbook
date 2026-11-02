#!/usr/bin/env python3
"""Read-only R4 integrated source/release boundary. NEVER an installer.

Full source candidate must be one manifest and one authenticated HTTPS
generated manager with no new public credentials or Moltbook send path.
This checks code shape, not live OMEN readiness, and grants NO authority.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater
import build_r4_manager_candidate as manager

CURRENT="v0.8.0-r3canary1"
CANDIDATE="v0.8.0-autonomy1"
FILES=frozenset((
    "bob-release-updater","bobctl","bob-activity-manager","navigation_shell.py",
    "bob_r4_policy.py","bob_r4_controls.py","bob_r4_projection.py",
    "bob_r4_reflections.py","bob_r4_decision.py","bob_r4_ledger.py",
    "bob_r4_suggestions.py","bob_r4_schema.py",
    "bob_r4_agent.py","bob_r4_producer.py","bob-r4-propose",
    "bob_r4_web.py","bob_r4_outbox.py",
    "bob_r4_publisher_adapter.py","bob-moltbook-publisher",
    "bob_r4_budget.py","bob_r4_remote_gate.py",
    "bob_r4_final_gate.py","bob_r4_installed_gate.py",
))
UNSAFE_WORKERS=frozenset((
    "bob-moltbook-scout","bob-r3-propose",
    "bob-r3-canary-arm","bob_r313c_adapter.py","bob_r3_canary_lock.py"))


def inspect(root:Path=ROOT) -> dict:
    root=Path(root)
    m=root/"releases/candidates/r4-autonomy1-consolidated.json"
    live=root/"releases/current.json"
    if m.is_symlink() or live.is_symlink():
        raise ValueError("r4_untrusted_manifest_symlink")
    candidate=json.loads(m.read_text("utf-8"))
    current=json.loads(live.read_text("utf-8"))
    if (current.get("release")!=CURRENT or
            candidate.get("release")!=CANDIDATE or
            candidate.get("from")!=CURRENT or
            candidate.get("format")!="bob-updater-v1" or
            candidate.get("restart_manager") is not True or
            type(candidate.get("files")) is not list):
        raise ValueError("r4_unsigned_release_chain")
    names=[x["name"] for x in candidate["files"]]
    if (set(names)!=FILES or len(names)!=len(FILES) or
            set(names)&UNSAFE_WORKERS or
            "bob_r4_verified_send_lab.py" in names):
        raise ValueError("r4_source_scope_unreviewed")
    expected={
        "bob-activity-manager":("builder","scripts/build_r4_manager_candidate.py",0),
        "navigation_shell.py":("builder","scripts/build_r4_manager_candidate.py",1),
    }
    for item in candidate["files"]:
        name=item["name"]
        origin=(("source",item["source"]) if set(item)=={"name","source"}
                else ("builder",item["builder"],item["index"]) if
                set(item)=={"name","builder","index"} and type(item["index"]) is int
                else None)
        if name in expected:
            if origin!=expected[name]:
                raise ValueError("r4_manager_build_untrusted")
        else:
            path=(
                "scripts/bob_release_updater.py" if name=="bob-release-updater"
                else "src/bin/bobctl" if name=="bobctl"
                else "src/bin/bob-r4-propose" if name=="bob-r4-propose"
                else "src/bin/bob-moltbook-publisher" if name=="bob-moltbook-publisher"
                else "src/lib/bob/"+name)
            if origin!=("source",path):
                raise ValueError("r4_unreviewed_source_target")
    bundle,navigation=manager.build()
    if (not 0<len(bundle)<=524288 or
            not 0<len(navigation)<=524288 or
            b"serve_tls(Handler, HOST, PORT)" not in bundle or
            b"R4_CSRF_TOKEN = TOKEN" not in bundle or
            b"class Handler(R3HandlerMixin, _LegacyHandler):" not in bundle):
        raise ValueError("r4_https_generated_manager_unverified")
    controls=(root/"src/lib/bob/bob_r4_controls.py").read_text("utf-8")
    policy=(root/"src/lib/bob/bob_r4_policy.py").read_text("utf-8")
    web=(root/"src/lib/bob/bob_r4_web.py").read_text("utf-8")
    migration=(root/"src/lib/bob/bob_r4_schema.py").read_text("utf-8")
    updater_source=(root/"scripts/bob_release_updater.py").read_text("utf-8")
    install_guard=(root/"scripts/r4_install_guard.py").read_text("utf-8")
    preinstall=(root/"scripts/report_r4_preinstall.py").read_text("utf-8")
    bobctl=(root/"src/bin/bobctl").read_text("utf-8")
    if ("INSTALL_HOOK_COMPILED_OFF=False" not in migration
            or "r4_apply_guarded_schema(" not in updater_source
            or '"phase":"migrated"' not in updater_source
            or '"v0.8.0-autonomy1": "https"' not in updater_source
            or '"v0.8.0-autonomy1": "https"' not in bobctl
            or "verify_backup_evidence(" not in install_guard
            or "def run_migration(" not in install_guard
            or "publisher_inactive:" not in install_guard
            or "not preflight_r4_installation()" not in updater_source
            or "from report_r4_preinstall import inspect" not in updater_source
            or "def signed_r3_canary()" not in preinstall
            or "def existing_worker_topology()" not in preinstall
            or "def effective_original_publisher_units()" not in preinstall
            or "def no_incomplete_update()" not in preinstall):
        raise ValueError("r4_source_migration_updater_chain_unverified")
    publisher=(root/"src/bin/bob-moltbook-publisher").read_text("utf-8")
    adapter=(root/"src/lib/bob/bob_r4_publisher_adapter.py").read_text("utf-8")
    outbox=(root/"src/lib/bob/bob_r4_outbox.py").read_text("utf-8")
    remote=(root/"src/lib/bob/bob_r4_remote_gate.py").read_text("utf-8")
    budget=(root/"src/lib/bob/bob_r4_budget.py").read_text("utf-8")
    if ("MAX_PREFLIGHT=timedelta(seconds=90)" not in remote or
            "R4_GLOBAL_DAILY_CAP=4" not in budget or
            "R4_MIN_GAP=timedelta(minutes=20)" not in budget):
        raise ValueError("r4_remote_or_counted_budget_source_drift")
    if (publisher.count("R4_SINGLE_PUBLISHER_COMPILED_OFF = True")!=1
            or "if not R4_SINGLE_PUBLISHER_COMPILED_OFF:" not in publisher
            or "R313C_INTEGRATION_COMPILED_OFF = False" not in publisher
            or publisher.count("def api(")!=1
            or "R4_REAL_DISPATCH_COMPILED_OFF=True" not in adapter
            or "R4_EXACT_OWNER_SEND_COMPILED_OFF=True" not in adapter
            or "PUBLIC_DISPATCH_COMPILED_OFF=True" not in outbox
            or "from bob_r4_final_gate import" not in adapter
            or "from bob_r4_installed_gate import verify" not in adapter):
        raise ValueError("r4_original_publisher_scope_not_compiled_off")
    if (not "AUTO_ENGINE_COMPILED_OFF=True" in controls or
            not "dispatch_authorized: bool = False" in policy or
            "Authorization: Bearer" in web or
            "from bob_moltbook_api import" in web or
            "R4HandlerMixin" not in web):
        raise ValueError("r4_source_default_off_unverified")
    digests={}
    for item in candidate["files"]:
        data=updater.release_bytes(root,item)
        if not 0<len(data)<=524288:
            raise ValueError("r4_oversize_release_file")
        digests[item["name"]]=hashlib.sha256(data).hexdigest()
    return {
        "format":"r4-source-candidate-v1",
        "current_unchanged":current["release"],
        "candidate":candidate["release"],
        "files":len(digests),
        "exact_https_generated_manager":True,
        "legacy_r3_publisher_not_replaced":True,
        "all_new_auto_modes_compiled_off":True,
        "candidate_source_build":"PASS",
        "install_authorized":False,
        "real_social_action_authorized":False,
        "legacy_queue_or_database_modified":False,
        "verified_source_hashes":digests,
    }


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r4_candidate.py --check")
        return 2
    try:
        info=inspect()
    except (OSError,ValueError,TypeError,KeyError,ImportError,SyntaxError,
            json.JSONDecodeError,UnicodeError):
        print("R4 CANDIDATE: REFUSED")
        return 1
    print("R4 AUTONOMY1 SOURCE CANDIDATE (NO INSTALL)")
    for key in ("current_unchanged","candidate","files",
                "candidate_source_build","exact_https_generated_manager",
                "all_new_auto_modes_compiled_off"):
        print(key.replace("_"," ")+":",info[key])
    print("New real Moltbook action authority: NONE")
    print("OMEN database, registry, services or HTTPS listener changed: NO")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
