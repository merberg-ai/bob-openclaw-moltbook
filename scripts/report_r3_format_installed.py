#!/usr/bin/env python3
"""Read-only signed R3 format1 installation check; no publishing or service action.

The previous diag1 report's accepted HTTPS and timer-owner checks are reused.
Only the exact signed package and newly reviewed response-format logic differ.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater
import r3_service_handoff as handoff
import report_r3_diagnostic_installed as diag

RELEASE="v0.8.0-r3format1"


def _signed() -> bool:
    try:
        return (updater.registry()["release"]==RELEASE and
                handoff._installed_cutover_off())
    except (OSError,ValueError,KeyError,TypeError):
        return False


def _exact_package() -> bool:
    if not _signed():
        return False
    try:
        with zipfile.ZipFile(updater.BIN/"bob_r3_package.pyz") as item:
            body=item.read("bob_v08/r313d_producer.py")
            return (len(body)<=65536
                    and b"def r3_decision_prompt(" in body
                    and b"def _shape_reason(" in body
                    and b"r3_decision_prompt(chosen)" in body
                    and b"decision_"+b"classification" in body)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile):
        return False


def _https() -> bool:
    try:
        return updater.healthy(updater.authorization(),release=RELEASE)
    except (OSError,ValueError,TypeError):
        return False


def inspect(*,owner=handoff._owner, installed=_signed,
            package=_exact_package, health=_https,
            controls=diag._authenticated_r3_https, units=diag._units_ok):
    return diag.inspect(owner=owner,installed=installed,package=package,
                        health=health,controls=controls,units=units)


def main(args=None):
    args=sys.argv[1:] if args is None else args
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r3_format_installed.py --check")
        return 2
    try:
        result=inspect()
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        print("R3 FORMAT1 INSTALLED: NOT_VERIFIED")
        return 1
    print("R3 FORMAT1 SIGNED INSTALLATION (READ ONLY)")
    for key in ("account","signed_r3_diagnostic_package",
                "authenticated_https_health","authenticated_r3_controls",
                "r3_proposal_only_timer","acceptance"):
        print(key.replace("_"," ")+":",result[key])
    print("Database, service schedule, publisher or credentials changed: NO")
    print("R3 real public publishing authorized: NO")
    return 0 if result["acceptance"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
