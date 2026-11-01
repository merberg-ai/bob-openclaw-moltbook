#!/usr/bin/env python3
"""Read-only installed acceptance for signed R3 skip1 proposal-only repair.

No producer invocation, service action, database mutation or Moltbook request.
The frozen installed hash registry must bind the exact reviewed archive.
"""
from __future__ import annotations

from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as upd
import r3_service_handoff as handoff
import report_r3_diagnostic_installed as diag

RELEASE="v0.8.0-r3skip1"


def _verified_release() -> bool:
    try:
        return (upd.registry()["release"]==RELEASE
                and handoff._installed_cutover_off()
                and upd.manager_transport(RELEASE)=="https")
    except (OSError,ValueError,KeyError,TypeError):
        return False


def _package() -> bool:
    if not _verified_release():
        return False
    try:
        with zipfile.ZipFile(upd.BIN/"bob_r3_package.pyz") as archive:
            code=archive.read("bob_v08/r313d_producer.py")
            return (len(code)<=65536
                    and b"def record_verified_skip(" in code
                    and b"read_observation(source_dir, observed.run_id)" in code
                    and b"event='r313d_skip'" in code
                    and b"return record_verified_skip(db, DATA, chosen, at=instant)" in code
                    and b"NO_PRODUCTION_DISPATCH = True" in code)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile):
        return False


def _https() -> bool:
    try:
        return upd.healthy(upd.authorization(),release=RELEASE)
    except (OSError,ValueError,TypeError):
        return False


def inspect(*,owner=handoff._owner, installed=_verified_release,
            package=_package, health=_https,
            controls=diag._authenticated_r3_https, units=diag._units_ok):
    return diag.inspect(owner=owner,installed=installed,package=package,
                        health=health,controls=controls,units=units)


def main(argv=None) -> int:
    args=sys.argv[1:] if argv is None else argv
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r3_skip_installed.py --check")
        return 2
    try:
        result=inspect()
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        print("R3 SKIP1 INSTALLED: NOT_VERIFIED")
        return 1
    print("R3 SKIP1 SIGNED INSTALLATION (READ ONLY)")
    for name in ("account","signed_r3_diagnostic_package",
                 "authenticated_https_health","authenticated_r3_controls",
                 "r3_proposal_only_timer","acceptance"):
        print(name.replace("_"," ")+":",result[name])
    print("No systemd change, publisher replacement, database migration or Moltbook write")
    print("Bob proposals already in /r3 remain intact")
    print("R3 real public publishing authorized: NO")
    return 0 if result["acceptance"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
