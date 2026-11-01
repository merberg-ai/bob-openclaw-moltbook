#!/usr/bin/env python3
"""R3 one-proposal-producer handoff: OFF-first, exact-name owner-only gate.

No additional Moltbook publisher is created. The *existing* credentialed
publisher and Scout timers are NEVER stopped, restarted, disabled, replaced or
reenabled by this file. Only the distinct R2 shadow decision timer is changed
at an explicitly authorized proposal-only handoff; newly installed R3 units
are not enabled by the updater and all real send gates must remain hard Off.

--check: pure, read-only; no private files created.
--apply: requires real installed hash-verified cutover1, exact source hard-Off,
         strict effective unit states, terminal consent and private journal.
--recover: restore previous R2 decision timer after interrupted handoff,
           preserving all SQLite history and Bob proposals. No DB restoration.
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater
import report_r3_consolidated_candidate as candidate

SERVICE="bob-r3-propose.service"
TIMER="bob-r3-propose.timer"
SHADOW_TIMER="bob-v08-shadow.timer"
SHADOW_SERVICE="bob-v08-shadow.service"
PUBLISHER_TIMER="bob-moltbook-publisher.timer"
PUBLISHER_SERVICE="bob-moltbook-publisher.service"
SCOUT_TIMER="bob-moltbook-scout.timer"
COMPETITOR_TIMER="bob-r3-candidate-publisher.timer"
COMPETITOR_SERVICE="bob-r3-candidate-publisher.service"
EXACT_UNITS=(SERVICE,TIMER,SHADOW_TIMER,SHADOW_SERVICE,PUBLISHER_TIMER,
             PUBLISHER_SERVICE,SCOUT_TIMER,COMPETITOR_TIMER,COMPETITOR_SERVICE)
HOME=Path.home()
UNITS_DIR=HOME/".config/systemd/user"
STATE_DIR=HOME/".local/state/bob-r3-handoff"
JOURNAL=STATE_DIR/"journal.json"
LOCK=STATE_DIR/"lock"
SYSTEMD_TIMEOUT=14
ENABLED=frozenset(("enabled","enabled-runtime"))
INERT_ENABLED=frozenset(("disabled","masked","masked-runtime","not-found"))
UNIT_TEXT={
    SERVICE: """[Unit]
Description=Bob R3 proposal-only OpenClaw decision (never a publisher)
After=openclaw-gateway.service
ConditionPathExists=%h/.config/moltbook/activity-queue.sqlite3

[Service]
Type=oneshot
ExecStart=%h/.local/bin/bob-r3-propose --once
UMask=0077
TimeoutStartSec=180
NoNewPrivileges=yes
""",
    TIMER: """[Unit]
Description=Bob R3 reviewed proposal-only schedule

[Timer]
Unit=bob-r3-propose.service
OnUnitInactiveSec=35min
RandomizedDelaySec=2min
AccuracySec=1min
Persistent=false

[Install]
WantedBy=timers.target
""",
}
SENSITIVE=frozenset((PUBLISHER_TIMER,PUBLISHER_SERVICE,SCOUT_TIMER))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _owner() -> bool:
    try:
        identity=pwd.getpwuid(os.geteuid())
        return (os.geteuid()!=0 and identity.pw_name=="openclaw"
                and identity.pw_dir==str(HOME))
    except (OSError,KeyError,ValueError):
        return False


def _trusted_dir(path: Path, *, strict: bool=False) -> bool:
    try:
        info=path.lstat()
        return (stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid()
                and not info.st_mode & (0o077 if strict else 0o022))
    except OSError:
        return False


def _validate_template() -> None:
    if set(UNIT_TEXT)!={SERVICE,TIMER}:
        raise ValueError("unreviewed_handoff_units")
    if (UNIT_TEXT[SERVICE].count("ExecStart=")!=1 or
            "ExecStart=%h/.local/bin/bob-r3-propose --once" not in
            UNIT_TEXT[SERVICE]):
        raise ValueError("unreviewed_proposal_binary")
    if (UNIT_TEXT[TIMER].count("Unit=")!=1
            or "Unit=bob-r3-propose.service" not in UNIT_TEXT[TIMER]):
        raise ValueError("unreviewed_proposal_timer_target")
    for label,body in UNIT_TEXT.items():
        if any(forbidden in body for forbidden in (
            "bob-moltbook-publisher", "curl ", "wget ", "moltbook.com",
            "Environment=", "ExecStartPre=", "ExecStartPost=",
            "WantedBy=multi-user.target")):
            raise ValueError("unsafe_proposal_unit")
        if len(body.encode())>8192 or "\r" in body or "\0" in body:
            raise ValueError("unreviewed_proposal_unit_size")


def _installed_cutover_off() -> bool:
    """Only source-untrusted installed bytes are inspected, never imported."""
    try:
        state=updater.registry()
        if state["release"]!="v0.8.0-cutover1" or not updater.live_ok(state):
            return False
        if updater.manager_transport(state["release"])!="https":
            return False
        for name,(constant,expected) in (
            ("bob-moltbook-publisher",("R313C_INTEGRATION_COMPILED_OFF",True)),
            ("bob_r312_adapter.py",("R312_REAL_DISPATCH",False)),
            ("bob_r313c_adapter.py",("R313C_REAL_DISPATCH",False)),
            ("bob_r313d_owner.py",("R3_AUTO_UI_COMPILED_OFF",True)),
        ):
            if candidate._literal_constant(updater.BIN/name,constant) is not expected:
                return False
        return True
    except (OSError,ValueError,TypeError,KeyError,SyntaxError):
        return False


@dataclass(frozen=True)
class Snapshot:
    load: str
    active: str
    enabled: str


def _snapshot(name: str, *, run=subprocess.run) -> Snapshot:
    if name not in EXACT_UNITS:
        raise ValueError("unreviewed_systemd_unit")
    try:
        p=run(
            ["systemctl","--user","show",name,"--no-pager",
             "--property=LoadState,ActiveState,UnitFileState"],
            capture_output=True,text=True,timeout=4,check=False)
        if p.returncode or not isinstance(p.stdout,str) or len(p.stdout)>1200:
            raise ValueError("systemd_probe_unavailable")
        fields=dict(line.split("=",1) for line in p.stdout.splitlines()
                    if line.count("=")==1 and line.split("=",1)[0] in
                    ("LoadState","ActiveState","UnitFileState"))
        if set(fields)!={"LoadState","ActiveState","UnitFileState"}:
            raise ValueError("systemd_probe_incomplete")
        return Snapshot(fields["LoadState"],fields["ActiveState"],
                        fields["UnitFileState"])
    except (OSError,subprocess.TimeoutExpired):
        raise ValueError("systemd_probe_unavailable") from None


def _clear_absent(s: Snapshot) -> bool:
    return s.active=="inactive" and (
        s.load=="not-found" or s.enabled in INERT_ENABLED)


def assess(states: dict[str, Snapshot]) -> tuple[str,...]:
    """Pure pre-activation review. Reject all ambiguous or competing owners."""
    _validate_template()
    if set(states)!=set(EXACT_UNITS):
        return ("unit_inventory_incomplete",)
    blockers=[]
    for name in (PUBLISHER_TIMER,SCOUT_TIMER,SHADOW_TIMER):
        x=states[name]
        if x.load!="loaded" or x.active!="active" or x.enabled not in ENABLED:
            blockers.append(name.replace(".","_")+"not_active_enabled")
    if states[PUBLISHER_SERVICE].active not in ("inactive",):
        blockers.append("publisher_service_busy_or_unknown")
    if states[SHADOW_SERVICE].active!="inactive":
        blockers.append("shadow_decision_in_flight")
    for name in (SERVICE,TIMER):
        x=states[name]
        # This is the initial handoff: untracked new service names must not
        # already exist or shadow an operator-installed definition.
        if x.load!="not-found" or x.active!="inactive":
            blockers.append("r3_proposal_unit_already_installed_or_active")
    for name in (COMPETITOR_SERVICE,COMPETITOR_TIMER):
        if not _clear_absent(states[name]):
            blockers.append("competing_r3_publisher_unit")
    return tuple(sorted(set(blockers)))


def _status_all(probe=_snapshot) -> dict[str,Snapshot]:
    return {name:probe(name) for name in EXACT_UNITS}


def _cmd(args: tuple[str,...], *, run=subprocess.run) -> None:
    """Fixed complete allowlist; no shell, no caller-selected unit arguments."""
    allowed={
        ("daemon-reload",),
        ("disable","--now",SHADOW_TIMER),
        ("enable","--now",SHADOW_TIMER),
        ("disable","--now",TIMER),
        ("enable","--now",TIMER),
    }
    if args not in allowed:
        raise ValueError("unreviewed_systemd_operation")
    p=run(["systemctl","--user",*args],capture_output=True,
          text=True,timeout=SYSTEMD_TIMEOUT,check=False)
    if p.returncode:
        raise ValueError("reviewed_systemd_operation_failed")


def _save(path: Path, data: bytes, *, mode=0o600) -> None:
    if path.is_symlink():
        raise ValueError("symlinked_handoff_destination")
    fd,tmp=tempfile.mkstemp(prefix=".r3-handoff-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            os.fchmod(out.fileno(),mode)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp,path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def _journal(phase: str) -> None:
    data={"format":"bob-r3-proposal-handoff-v1","phase":phase,
          "old_shadow_timer":"enabled_active",
          "units":{name:_digest(value.encode()) for name,value in UNIT_TEXT.items()},
          "r3_real_publishing_authorized":False}
    _save(JOURNAL,(json.dumps(data,sort_keys=True)+"\n").encode())


def _read_journal() -> dict:
    if JOURNAL.is_symlink() or not JOURNAL.is_file():
        raise ValueError("handoff_journal_not_private_file")
    jstat=JOURNAL.stat()
    if (jstat.st_uid!=os.geteuid() or jstat.st_nlink!=1 or
            jstat.st_mode & 0o077 or jstat.st_size>8192):
        raise ValueError("handoff_journal_untrusted")
    data=json.loads(JOURNAL.read_text(encoding="utf-8"))
    if (data.get("format")!="bob-r3-proposal-handoff-v1"
        or data.get("old_shadow_timer")!="enabled_active"
        or data.get("phase") not in
           ("prepared","files_installed","shadow_disabled","activated",
            "complete","rolled_back")
        or data.get("units")!={name:_digest(body.encode())
                                for name,body in UNIT_TEXT.items()}
        or data.get("r3_real_publishing_authorized") is not False):
        raise ValueError("untrusted_handoff_journal")
    return data


def _lock() -> int:
    if not _trusted_dir(STATE_DIR,strict=True):
        raise ValueError("untrusted_handoff_state_directory")
    fd=os.open(LOCK,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    st=os.fstat(fd)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid()
            or st.st_mode & 0o077):
        os.close(fd)
        raise ValueError("untrusted_handoff_lock")
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _unit_dir_ready() -> bool:
    return (_trusted_dir(HOME)
            and _trusted_dir(HOME/".config")
            and _trusted_dir(HOME/".config/systemd")
            and _trusted_dir(UNITS_DIR))


def activate(*, probe=_snapshot, control=_cmd,
             verified=_installed_cutover_off) -> str:
    """Owner-approved only. No generic systemd control and NO Moltbook POST."""
    if not _owner() or not verified() or not _unit_dir_ready():
        raise ValueError("untrusted_handoff_owner_or_installed_release")
    if not _trusted_dir(STATE_DIR,strict=True):
        raise ValueError("handoff_state_not_prepared")
    fd=_lock()
    try:
        if JOURNAL.exists() or JOURNAL.is_symlink():
            raise ValueError("existing_handoff_journal_requires_review")
        if any((UNITS_DIR/name).exists() or
               (UNITS_DIR/name).is_symlink() for name in UNIT_TEXT):
            raise ValueError("existing_proposal_unit_files")
        states=_status_all(probe)
        blockers=assess(states)
        if blockers:
            raise ValueError("handoff_state_requires_review")
        _journal("prepared")
        try:
            for name,body in UNIT_TEXT.items():
                path=UNITS_DIR/name
                if path.exists() or path.is_symlink():
                    raise ValueError("proposal_unit_collision")
                _save(path,body.encode())
            _journal("files_installed")
            control(("daemon-reload",))
            control(("disable","--now",SHADOW_TIMER))
            _journal("shadow_disabled")
            control(("enable","--now",TIMER))
            _journal("activated")
            end=_status_all(probe)
            if (end[PUBLISHER_TIMER].active!="active" or
                    end[SCOUT_TIMER].active!="active" or
                    end[TIMER].active!="active" or
                    end[TIMER].enabled not in ENABLED or
                    end[SHADOW_TIMER].active!="inactive" or
                    end[SHADOW_TIMER].enabled in ENABLED or
                    not _clear_absent(end[COMPETITOR_TIMER])):
                raise ValueError("handoff_postflight_units_unverified")
            _journal("complete")
            return "proposal_only_timer_active"
        except (OSError,ValueError,subprocess.SubprocessError):
            # Any normal failure attempts code/unit-only rollback; failure to
            # restore leaves a durable journal for explicit owner --recover.
            try:
                _restore(control=control,probe=probe)
                _journal("rolled_back")
                return "rolled_back"
            except (OSError,ValueError,subprocess.SubprocessError):
                raise ValueError("handoff_recovery_required") from None
    finally:
        os.close(fd)


def _restore(*,control=_cmd,probe=_snapshot) -> None:
    """Restore R2 schedule, never touch publisher, Scout, Bob DB or keys."""
    info=_read_journal()
    if info["phase"]=="rolled_back":
        return
    if probe(SERVICE).active!="inactive":
        raise ValueError("r3_proposal_worker_in_flight")
    # An interruption may happen before the new timer is even loaded. Only
    # stop it if running/enabled; unfamiliar states fail closed rather than
    # letting a possibly armed timer survive unit removal.
    state=probe(TIMER)
    if state.active=="active" or state.enabled in ENABLED:
        control(("disable","--now",TIMER))
    elif not (state.active=="inactive" and state.load in ("loaded","not-found")
              and state.enabled in INERT_ENABLED):
        raise ValueError("r3_timer_state_untrusted_during_recovery")
    for name,body in UNIT_TEXT.items():
        path=UNITS_DIR/name
        if path.is_symlink():
            raise ValueError("handoff_unit_symlink_drift")
        if path.exists():
            if (not path.is_file() or _digest(path.read_bytes())!=
                    _digest(body.encode())):
                raise ValueError("handoff_unit_changed_since_activation")
            path.unlink()
    control(("daemon-reload",))
    control(("enable","--now",SHADOW_TIMER))


def recover(*,control=_cmd,probe=_snapshot,verified_owner=_owner) -> str:
    """Explicit owner recovery even if cutover code already rolled back."""
    if not verified_owner() or not _unit_dir_ready() or not _trusted_dir(STATE_DIR,strict=True):
        raise ValueError("untrusted_handoff_recovery_owner")
    fd=_lock()
    try:
        row=_read_journal()
        if row["phase"]=="rolled_back":
            return "already_rolled_back"
        _restore(control=control,probe=probe)
        _journal("rolled_back")
        return "shadow_schedule_restored"
    finally:
        os.close(fd)


def inspect(*,probe=_snapshot,verified=_installed_cutover_off) -> dict:
    """Read-only, fail closed. A future host MUST have full gate before apply."""
    try:
        states=_status_all(probe)
        blockers=list(assess(states))
    except (OSError,ValueError,TypeError):
        blockers=["systemd_unit_inspection_unavailable"]
    try:
        release_off=bool(verified())
    except (OSError,ValueError,TypeError):
        release_off=False
    if not release_off:
        blockers.append("installed_cutover1_hard_off_unverified")
    if not _unit_dir_ready():
        blockers.append("user_systemd_unit_directory_unavailable")
    if JOURNAL.exists() or JOURNAL.is_symlink():
        blockers.append("existing_handoff_journal")
    return {
        "format":"bob-r3-proposal-handoff-plan-v1",
        "publisher_timer_change":False,
        "scout_timer_change":False,
        "r2_shadow_timer_requires_explicit_handoff":True,
        "r3_proposal_timer_default_enabled":False,
        "r3_proposal_service_is_publisher":False,
        "installed_cutover1_hard_off_verified":release_off,
        "blockers":sorted(set(blockers)),
        "owner_can_review_handoff":not blockers,
        "r3_real_publishing_authorized":False,
        "services_changed_by_inspection":0,
    }


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args not in (["--check"],["--apply"],["--recover"]):
        print("Usage: python3 scripts/r3_service_handoff.py "
              "--check|--apply|--recover")
        return 2
    if not _owner():
        print("R3 HANDOFF REFUSED: normal openclaw owner required")
        return 1
    if args==["--check"]:
        report=inspect()
        print("R3 PROPOSAL TIMER HANDOFF (READ ONLY)")
        print("installed signed cutover1 hard Off:",
              report["installed_cutover1_hard_off_verified"])
        print("preflight blockers:", ",".join(report["blockers"]) or "none")
        print("legacy publisher and Scout touched: NO")
        print("new proposal timer installed or enabled: NO")
        print("R3 real publishing authorized: NO")
        return 0 if report["owner_can_review_handoff"] else 1
    if not sys.stdin.isatty():
        print("R3 HANDOFF REFUSED: interactive owner approval required")
        return 1
    phrase=("ACTIVATE R3 PROPOSALS" if args==["--apply"]
            else "RECOVER R3 SHADOW")
    if input("Type "+phrase+" to confirm this exact unit-only action: ")!=phrase:
        print("R3 HANDOFF REFUSED: confirmation absent")
        return 1
    try:
        if args==["--apply"]:
            if not STATE_DIR.exists():
                if STATE_DIR.is_symlink():
                    raise ValueError("symlinked_handoff_state")
                STATE_DIR.mkdir(mode=0o700,parents=True)
            result=activate()
        else:
            result=recover()
        print("R3 HANDOFF:",result)
        print("Legacy publisher, Moltbook, SQLite history untouched by handoff")
        return 0 if result in ("proposal_only_timer_active",
                               "shadow_schedule_restored","already_rolled_back") else 1
    except (OSError,ValueError,TypeError,subprocess.SubprocessError):
        print("R3 HANDOFF REFUSED: unit/owner/registry boundary not verified")
        print("No automatic retry; inspect private handoff journal before recovery")
        return 1


if __name__=="__main__":
    raise SystemExit(main())
