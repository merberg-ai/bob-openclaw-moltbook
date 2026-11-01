#!/usr/bin/env python3
"""Read-only host acceptance of signed R3 diagnostic-only release.

Never starts services, reads Moltbook credentials or writes to public API.
This validates the *installed* archive, authenticated HTTPS and existing
proposal-only service topology, not successful Bob model generation.
"""
from __future__ import annotations

from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as upd
import r3_service_handoff as handoff
from report_r3_cutover_installed import _authenticated_r3_https

RELEASE="v0.8.0-r3diag1"


def _verified_release() -> bool:
    try:
        return (upd.registry()["release"]==RELEASE
                and handoff._installed_cutover_off())
    except (OSError,ValueError,KeyError,TypeError):
        return False


def _diagnostic_package_present() -> bool:
    """Only inspect the archive after the installed SHA registry is verified."""
    if not _verified_release():
        return False
    try:
        with zipfile.ZipFile(upd.BIN/"bob_r3_package.pyz") as archive:
            names=set(archive.namelist())
            if "bob_v08/r313d_producer.py" not in names:
                return False
            code=archive.read("bob_v08/r313d_producer.py")
            return (len(code)<=65536
                    and b'"openclaw_"+_safe_error_reason(exc)' in code
                    and (b'"decision_"+_safe_error_reason(exc)' in code
                         or b'"decision_"+classification' in code))
    except (OSError,ValueError,KeyError,zipfile.BadZipFile):
        return False


def _units_ok() -> bool:
    try:
        st=handoff._status_all()
        for name in (handoff.PUBLISHER_TIMER,handoff.SCOUT_TIMER,handoff.TIMER):
            s=st[name]
            if s.load!="loaded" or s.active!="active" or s.enabled not in handoff.ENABLED:
                return False
        return (st[handoff.PUBLISHER_SERVICE].active=="inactive"
                and st[handoff.SERVICE].active in ("inactive","failed")
                and st[handoff.SHADOW_SERVICE].active=="inactive"
                and st[handoff.SHADOW_TIMER].active=="inactive"
                and st[handoff.SHADOW_TIMER].enabled not in handoff.ENABLED
                and handoff._clear_absent(st[handoff.COMPETITOR_TIMER])
                and handoff._clear_absent(st[handoff.COMPETITOR_SERVICE]))
    except (OSError,ValueError,TypeError):
        return False


def _https_ok() -> bool:
    try:
        return upd.healthy(upd.authorization(),release=RELEASE)
    except (OSError,ValueError,TypeError):
        return False


def inspect(*,owner=handoff._owner, installed=_verified_release,
            package=_diagnostic_package_present, health=_https_ok,
            controls=_authenticated_r3_https, units=_units_ok) -> dict:
    result={
        "account":"unverified",
        "signed_r3_diagnostic_package":"unverified",
        "authenticated_https_health":"unverified",
        "authenticated_r3_controls":"unverified",
        "r3_proposal_only_timer":"unverified",
        "acceptance":"NOT_VERIFIED",
        "r3_real_publication_authorized":False,
        "host_or_database_changed":False,
        "moltbook_requests":0,
    }
    if not owner():
        return result
    result["account"]="verified"
    if not installed() or not package():
        return result
    result["signed_r3_diagnostic_package"]="PASS"
    if not health():
        return result
    result["authenticated_https_health"]="PASS"
    if not controls():
        return result
    result["authenticated_r3_controls"]="PASS"
    if not units():
        return result
    result["r3_proposal_only_timer"]="ACTIVE"
    result["acceptance"]="PASS"
    return result


def main(args=None) -> int:
    args=sys.argv[1:] if args is None else args
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r3_diagnostic_installed.py --check")
        return 2
    try:
        data=inspect()
    except (OSError,ValueError,TypeError,KeyError,RuntimeError):
        print("R3 DIAGNOSTICS INSTALLED: NOT_VERIFIED")
        return 1
    print("R3 DIAGNOSTICS SIGNED INSTALLATION (READ ONLY)")
    for name in ("account","signed_r3_diagnostic_package",
                 "authenticated_https_health","authenticated_r3_controls",
                 "r3_proposal_only_timer","acceptance"):
        print(name.replace("_"," ")+":",data[name])
    print("Database, systemd, publisher, credentials modified: NO")
    print("Moltbook requests: NO")
    print("R3 real public publishing authorized: NO")
    return 0 if data["acceptance"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
