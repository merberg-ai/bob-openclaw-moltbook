#!/usr/bin/env python3
"""Repair the FIRST R3 proposal timer tick, never touch Moltbook publishing.

Source-only until the owner explicitly authorizes --apply on OpenClawLab.
The previously installed handoff unit and journal remain byte-for-byte fixed.
A single pinned systemd user-timer drop-in seeds the first monotonic tick;
the original OnUnitInactiveSec=35min handles all following cycles.

--check reads only. --apply requires exact owner confirmation. --undo
removes ONLY this exact drop-in before the original handoff --recover.
"""
from __future__ import annotations

from pathlib import Path
import os
import stat
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import r3_service_handoff as h

D= h.UNITS_DIR/(h.TIMER+".d")
F= D/"10-first-run.conf"
BODY=b"[Timer]\nOnActiveSec=2min\n"
EXPECTED=("loaded","active")


def _dropin() -> bool:
    if D.is_symlink():
        raise ValueError("unsafe_dropin_directory")
    if not D.exists():
        return False
    if not h._trusted_dir(D,strict=True):
        raise ValueError("untrusted_dropin_directory")
    if set(D.iterdir())!={F} or F.is_symlink():
        raise ValueError("unreviewed_dropin")
    info=F.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid()
            or info.st_nlink!=1 or info.st_mode & 0o077
            or F.read_bytes()!=BODY):
        raise ValueError("changed_dropin")
    return True


def _check(probe=h._snapshot, verified=h._installed_cutover_off) -> bool:
    if not h._owner() or not verified() or not h._unit_dir_ready():
        raise ValueError("owner_or_hard_off_release_not_verified")
    if not h._trusted_dir(h.STATE_DIR,strict=True):
        raise ValueError("untrusted_handoff_state")
    if h._read_journal()["phase"]!="complete":
        raise ValueError("handoff_not_complete")
    for name,text in h.UNIT_TEXT.items():
        p=h.UNITS_DIR/name
        if p.is_symlink() or not p.is_file():
            raise ValueError("original_unit_missing_or_symlink")
        info=p.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid()
                or info.st_mode & 0o077 or info.st_nlink!=1
                or p.read_bytes()!=text.encode()):
            raise ValueError("original_unit_hash_drift")
    states=h._status_all(probe)
    for name in (h.PUBLISHER_TIMER,h.SCOUT_TIMER,h.TIMER):
        state=states[name]
        if (state.load!="loaded" or state.active!="active"
                or state.enabled not in h.ENABLED):
            raise ValueError("required_timer_not_active")
    if (states[h.SERVICE].active!="inactive"
            or states[h.SHADOW_SERVICE].active!="inactive"
            or states[h.SHADOW_TIMER].active!="inactive"
            or states[h.SHADOW_TIMER].enabled in h.ENABLED
            or states[h.PUBLISHER_SERVICE].active!="inactive"):
        raise ValueError("worker_or_shadow_busy")
    for name in (h.COMPETITOR_TIMER,h.COMPETITOR_SERVICE):
        if not h._clear_absent(states[name]):
            raise ValueError("competing_publisher")
    return _dropin()


def _sysctl(operation):
    if operation not in ("daemon-reload","restart"):
        raise ValueError("unreviewed_systemd_action")
    cmd=(["systemctl","--user","daemon-reload"] if operation=="daemon-reload"
         else ["systemctl","--user","restart",h.TIMER])
    result=subprocess.run(cmd,capture_output=True,text=True,
                          timeout=15,check=False)
    if result.returncode:
        raise ValueError("proposal_timer_operation_failed")


def _has_deadline():
    result=subprocess.run(
        ["systemctl","--user","show",h.TIMER,
         "--property=NextElapseUSecMonotonic","--value"],
        capture_output=True,text=True,timeout=5,check=False)
    value=result.stdout.strip() if result.returncode==0 else ""
    return bool(value) and value not in ("0","0us","n/a","infinity","-")


def apply(*,probe=h._snapshot,verified=h._installed_cutover_off,
          sysctl=_sysctl,deadline=_has_deadline):
    fd=h._lock()
    try:
        was_present=_check(probe,verified)
        if not was_present:
            D.mkdir(mode=0o700)
            h._save(F,BODY)
        sysctl("daemon-reload")
        sysctl("restart")
        state=probe(h.TIMER)
        if state.active!="active" or state.enabled not in h.ENABLED or not deadline():
            raise ValueError("proposal_timer_next_activation_unverified")
        return "first_proposal_tick_scheduled"
    finally:
        os.close(fd)


def undo(*,probe=h._snapshot,verified=h._installed_cutover_off,
         sysctl=_sysctl):
    fd=h._lock()
    try:
        if not _check(probe,verified):
            return "no_bootstrap_to_remove"
        F.unlink()
        D.rmdir()
        sysctl("daemon-reload")
        sysctl("restart")
        return "bootstrap_removed_original_handoff_unchanged"
    finally:
        os.close(fd)


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args not in (["--check"],["--apply"],["--undo"]):
        print("Usage: python3 scripts/repair_r3_first_timer.py --check|--apply|--undo")
        return 2
    try:
        if args==["--check"]:
            present=_check()
            print("R3 FIRST-TICK REPAIR PRECHECK: PASS")
            print("Original signed handoff and publisher untouched: YES")
            print("Existing verified first-tick drop-in:",present)
            print("No host changes made")
            return 0
        if not sys.stdin.isatty():
            raise ValueError("interactive_owner_confirmation_required")
        expected=("REPAIR R3 FIRST TIMER" if args==["--apply"]
                  else "UNDO R3 FIRST TIMER")
        if input("Type "+expected+" to confirm: ")!=expected:
            raise ValueError("owner_confirmation_absent")
        result=apply() if args==["--apply"] else undo()
        print("R3 FIRST-TICK:",result)
        print("Moltbook publisher, Scout, historical jobs, credentials untouched")
        return 0
    except (OSError,ValueError,TypeError,subprocess.SubprocessError):
        print("R3 FIRST-TICK REFUSED: check original handoff and timer state")
        return 1


if __name__=="__main__":
    raise SystemExit(main())
