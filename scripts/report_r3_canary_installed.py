#!/usr/bin/env python3
"""Read-only signed exact R3 canary install acceptance, never publication.

A PASS means the scoped code is installed, NOT armed or sent. Public action
requires a separately queued exact manual job and owner TTY arm. All checks
rely on installed registry/bytes, original HTTPS dashboard and timer shape.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]
import bob_release_updater as upd
import r3_service_handoff as handoff
import report_r3_diagnostic_installed as diag
from report_r3_consolidated_candidate import _literal_constant

RELEASE="v0.8.0-r3canary1"
RUN="20261101T151033Z"
TARGET="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
SEAL="870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2"
EXPIRY="2026-11-05T00:00:00Z"
EXPECTED=frozenset((
    "bob-release-updater","bobctl","bob_r3_package.pyz",
    "bob_r3_canary_lock.py","bob_r313c_adapter.py",
    "bob-moltbook-publisher","bob-r3-canary-arm",
))


def _signed_scope() -> bool:
    try:
        state=upd.registry()
        if (state["release"]!=RELEASE or not upd.live_ok(state)
                or upd.manager_transport(RELEASE)!="https"):
            return False
        if not EXPECTED.issubset(state["files"]):
            return False
        constants=(
            ("bob-moltbook-publisher","R313C_INTEGRATION_COMPILED_OFF",False),
            ("bob_r313c_adapter.py","R313C_REAL_DISPATCH",False),
            ("bob_r313c_adapter.py","R3_EXACT_CANARY_COMPILED",True),
            ("bob_r312_adapter.py","R312_REAL_DISPATCH",False),
            ("bob_r313d_owner.py","R3_AUTO_UI_COMPILED_OFF",True),
        )
        for name,key,value in constants:
            if _literal_constant(upd.BIN/name,key) is not value:
                return False
        with zipfile.ZipFile(upd.BIN/"bob_r3_package.pyz") as archive:
            code=archive.read("bob_v08/r313c_candidate.py")
            if (b"exact_canary_run=None" not in code
                    or b"exact_canary_run_changed" not in code):
                return False
        spec=importlib.util.spec_from_file_location(
            "bob_r3_signed_canary_probe", upd.BIN/"bob_r3_canary_lock.py")
        if spec is None or spec.loader is None:
            return False
        # Do not execute unverified source: installed file digests were checked.
        # Instead inspect the immutable compiled PIN assignments in source.
        source=(upd.BIN/"bob_r3_canary_lock.py").read_text(encoding="utf-8")
        return all(x in source for x in (
            'run="'+RUN+'"', 'seal="'+SEAL+'"',
            'target="'+TARGET+'"', 'expires_utc="'+EXPIRY+'"',
            "def marker_valid(", "def installed_canary_ready(",
            "def still_pinned_for_send("))
    except (OSError,ValueError,TypeError,KeyError,ImportError,
            UnicodeError,zipfile.BadZipFile,SyntaxError):
        return False


def _https() -> bool:
    try:
        return upd.healthy(upd.authorization(),release=RELEASE)
    except (OSError,ValueError,TypeError):
        return False


def inspect(*,owner=handoff._owner, scope=_signed_scope,
            health=_https, controls=diag._authenticated_r3_https,
            units=diag._units_ok) -> dict:
    result={"format":"r3-exact-canary1-installed-v1",
            "signed_exact_scope":"not_verified",
            "authenticated_https":"not_verified",
            "owner_r3_controls":"not_verified",
            "existing_service_topology":"not_verified",
            "acceptance":"NOT_VERIFIED",
            "armed_by_install":False,
            "publisher_or_schema_migrated":False,
            "canary_public_post_sent_by_report":False}
    try:
        if not owner() or not scope():
            return result
        result["signed_exact_scope"]="PASS"
        if not health() or not controls() or not units():
            return result
        result["authenticated_https"]="PASS"
        result["owner_r3_controls"]="PASS"
        result["existing_service_topology"]="PASS"
        result["acceptance"]="PASS"
        return result
    except (OSError,ValueError,TypeError,KeyError):
        return result


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r3_canary_installed.py --check")
        return 2
    status=inspect()
    print(json.dumps(status,sort_keys=True,separators=(",",":")))
    print("Installation is not an ARM and is not publication.")
    return 0 if status["acceptance"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
