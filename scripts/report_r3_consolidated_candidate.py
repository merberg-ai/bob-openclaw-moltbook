#!/usr/bin/env python3
"""Source-only v0.8 R3 integration bundle audit. Never installs or publishes.

Checks a tightly allowlisted candidate manifest, installed-release CHHTTPS3
CHAIN in the repo, four hard-Off dispatch gates, HTTPS for updater/bobctl,
and builds the 12 declared files from reviewed local source. No credentials,
SQLite, systemd, Moltbook API, service restart or public POST.
This is NOT live host readiness or cutover authorization.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import bob_release_updater as updater

CANDIDATE = ROOT/"releases/candidates/r3-cutover1-integration-off.json"
EXPECTED = {
    "bob-release-updater": ("source", "scripts/bob_release_updater.py"),
    "bobctl": ("source", "src/bin/bobctl"),
    "bob_r312_adapter.py": ("source", "src/lib/bob/bob_r312_adapter.py"),
    "bob_r313c_adapter.py": ("source", "src/lib/bob/bob_r313c_adapter.py"),
    "bob_r313d_package.py": ("source", "src/lib/bob/bob_r313d_package.py"),
    "bob_r313d_owner.py": ("source", "src/lib/bob/bob_r313d_owner.py"),
    "bob_r313d_web.py": ("source", "src/lib/bob/bob_r313d_web.py"),
    "bob_r3_package.pyz": ("builder", "scripts/build_r313d_off_package.py", 0),
    "bob-r3-propose": ("builder", "scripts/build_r313d_off_package.py", 1),
    "bob-moltbook-publisher": ("source", "src/bin/bob-moltbook-publisher"),
    "bob-activity-manager": ("builder", "scripts/build_ch_https3_manager_candidate.py", 0),
    "navigation_shell.py": ("builder", "scripts/build_r313d_manager_candidate.py", 1),
}
OFF_CONSTANTS = {
    "src/bin/bob-moltbook-publisher": ("R313C_INTEGRATION_COMPILED_OFF", True),
    "src/lib/bob/bob_r312_adapter.py": ("R312_REAL_DISPATCH", False),
    "src/lib/bob/bob_r313c_adapter.py": ("R313C_REAL_DISPATCH", False),
    "src/lib/bob/bob_r313d_owner.py": ("R3_AUTO_UI_COMPILED_OFF", True),
}


def _literal_constant(path: Path, name: str):
    """Read the single top-level assignment; never import the publisher."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values=[]
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
                values.append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target,ast.Name) and node.target.id==name:
            values.append(node.value)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
    if len(values)!=1 or not isinstance(values[0],ast.Constant):
        raise ValueError("R3 compiled safety constant missing or nonliteral")
    value=values[0].value
    if type(value) is not bool:
        raise ValueError("R3 compiled safety constant is not boolean")
    return value


def inspect(*, root=ROOT, build=True) -> dict:
    """All data from explicit reviewed source paths; no caller-supplied path CLI."""
    current_path=root/"releases/current.json"
    manifest_path=root/"releases/candidates/r3-cutover1-integration-off.json"
    if current_path.is_symlink() or manifest_path.is_symlink():
        raise ValueError("symlinked release manifest")
    current=json.loads(current_path.read_text(encoding="utf-8"))
    proposed=json.loads(manifest_path.read_text(encoding="utf-8"))
    promoted=current.get("release") in ("v0.8.0-cutover1","v0.8.0-r3diag1","v0.8.0-r3format1","v0.8.0-r3skip1","v0.8.0-r3canary1","v0.8.0-autonomy1","v0.8.0-r4propose1")
    if current.get("release") not in (
            "v0.8.0-chhttps3","v0.8.0-cutover1","v0.8.0-r3diag1","v0.8.0-r3format1","v0.8.0-r3skip1","v0.8.0-r3canary1","v0.8.0-autonomy1","v0.8.0-r4propose1"):
        raise ValueError("unreviewed_source_release_or_promotion")
    if current.get("release")=="v0.8.0-r4propose1":
        patch=json.loads((root/"releases/candidates/r4-propose1-one-shot.json").read_text())
        if (current!=patch or patch.get("from")!="v0.8.0-autonomy1"
                or len(patch.get("files",[]))!=4
                or patch.get("restart_manager") is not True):
            raise ValueError("r4_proposal_patch_not_exact_reviewed_candidate")
    if current.get("release")=="v0.8.0-autonomy1":
        r4=json.loads((root/"releases/candidates/r4-autonomy1-consolidated.json").read_text())
        if (current!=r4 or r4.get("from")!="v0.8.0-r3canary1"
                or len(r4.get("files",[]))!=23
                or r4.get("restart_manager") is not True):
            raise ValueError("r4_promotion_does_not_match_reviewed_candidate")
    if current.get("release")=="v0.8.0-cutover1" and any(current.get(key)!=proposed.get(key) for key in (
            "format","release","from","files","restart_manager")):
        raise ValueError("promoted_r3_manifest_not_exact_reviewed_candidate")
    if (proposed.get("format")!="bob-updater-v1"
            or proposed.get("release")!="v0.8.0-cutover1"
            or proposed.get("from")!="v0.8.0-chhttps3"
            or proposed.get("restart_manager") is not True
            or type(proposed.get("notes")) is not str
            or type(proposed.get("files")) is not list
            or len(proposed["files"])!=len(EXPECTED)):
        raise ValueError("unexpected cutover candidate contract")
    targets={}
    for item in proposed["files"]:
        if not isinstance(item,dict) or not isinstance(item.get("name"),str):
            raise ValueError("unexpected candidate file entry")
        name=item["name"]
        if name not in EXPECTED or name in targets:
            raise ValueError("unexpected duplicate or extra release target")
        actual=(("source",item["source"]) if set(item)=={"name","source"}
                else ("builder",item["builder"],item["index"]) if
                set(item)=={"name","builder","index"} and type(item["index"]) is int
                else None)
        if actual != EXPECTED[name]:
            raise ValueError("candidate changed reviewed build or source path")
        targets[name]=item
    if set(targets)!=set(EXPECTED):
        raise ValueError("required source candidate file absent")
    if updater.manager_transport("v0.8.0-cutover1")!="https":
        raise ValueError("candidate HTTPS transport refused")
    # bobctl is source-verified here, not loaded (would probe host process env).
    controller=(root/"src/bin/bobctl").read_text(encoding="utf-8")
    if '"v0.8.0-cutover1": "https"' not in controller:
        raise ValueError("bobctl candidate HTTPS mode unavailable")
    exact=current.get("release") in ("v0.8.0-r3canary1","v0.8.0-autonomy1","v0.8.0-r4propose1")
    if exact:
        # The historic integration-off audit must NEVER label an exact
        # owner-arm canary as globally compiled Off, or as a cutover release.
        # Only narrowly pinned manual behavior may bypass the old importer gate.
        reviewed=json.loads((root/"releases/candidates/r3-canary1-exact-manual.json").read_text())
        candidate=current if current.get("release")=="v0.8.0-r3canary1" else reviewed
        if candidate!=reviewed:
            raise ValueError("canary_release_manifest_not_exact")
        required=dict(OFF_CONSTANTS)
        required["src/bin/bob-moltbook-publisher"]=(
            "R313C_INTEGRATION_COMPILED_OFF",False)
        for name,(variable,expected) in required.items():
            if _literal_constant(root/name,variable) is not expected:
                raise ValueError("R3 actual source send gate is not Off")
        if _literal_constant(root/"src/lib/bob/bob_r313c_adapter.py",
                             "R3_EXACT_CANARY_COMPILED") is not True:
            raise ValueError("canary_exact_source_flag_absent")
        lock=(root/"src/lib/bob/bob_r3_canary_lock.py").read_text()
        if not all(x in lock for x in (
                "20261101T151033Z",
                "870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2",
                "bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a",
                "2026-11-05T00:00:00Z",
                "def marker_valid(")):
            raise ValueError("canary_exact_source_lock_invalid")
    else:
        for name,(variable,expected) in OFF_CONSTANTS.items():
            if _literal_constant(root/name,variable) is not expected:
                raise ValueError("R3 actual source send gate is not Off")
    if "FINAL_NO_DUPLICATE_CLAIM" not in (root/"src/bin/bob-moltbook-publisher").read_text(encoding="utf-8"):
        raise ValueError("single-publisher final duplicate guard is absent")

    sha={}
    if build:
        # We deliberately use the exact same reviewed builder as the updater.
        # It only imports reviewed local builders and does not touch the host.
        for name,item in targets.items():
            data=updater.release_bytes(root,item)
            if not 0 < len(data)<=524288:
                raise ValueError("candidate file size refused")
            sha[name]=hashlib.sha256(data).hexdigest()
    return {
        "format":"bob-r3-cutover-integration-off-audit-v1",
        "source_candidate":"verified" if build else "manifest_verified",
        "from":"v0.8.0-chhttps3",
        "release":"v0.8.0-cutover1",
        "files_built":len(sha),
        "source_gates":"one_exact_manual_owner_arm_only" if exact else "four_hard_off",
        "single_existing_credentialed_publisher":True,
        "publisher_atomic_duplicate_guard_present":True,
        "dashboard_transport":"https_only",
        "releases_current_json_modified":promoted,
        "installed_files_or_systemd_modified":False,
        "private_db_or_credentials_read":False,
        "moltbook_requests":0,
        "r3_real_publishing_authorized":False,
        "ready_to_install_or_cutover":False,
        "source_hashes":sha,
    }


def main(argv=None):
    if (sys.argv[1:] if argv is None else argv) != ["--check"]:
        print("Usage: python3 scripts/report_r3_consolidated_candidate.py --check")
        return 2
    try:
        result=inspect()
    except (OSError,ValueError,TypeError,KeyError,ImportError,SyntaxError) as exc:
        print("R3 CONSOLIDATED CANDIDATE: REFUSED ("+type(exc).__name__+")")
        return 1
    print("R3 CONSOLIDATED SOURCE CANDIDATE (NO INSTALL)")
    for key in ("source_candidate","from","release","files_built",
                "source_gates","single_existing_credentialed_publisher",
                "publisher_atomic_duplicate_guard_present",
                "dashboard_transport"):
        print(key.replace("_"," ")+":",result[key])
    print("R3 manifest source promotion observed:", result["releases_current_json_modified"])
    print("Installed OMEN host changed by audit: NO")
    print("Private DB, credentials, systemd or Moltbook touched: NO")
    print("R3 real publishing authorized: NO")
    print("Ready for an owner cutover update: NO")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
