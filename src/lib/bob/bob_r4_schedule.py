"""R4 proposal-only systemd schedule: source-reviewed, OFF-first owner gate.

THIS MODULE DOES NOT create Moltbook requests or publish jobs. Systemd may
invoke --once only after a separate, typed owner enable; --once delegates to
the signed R4 producer with existing exact model/source/ledger validation.
R3, Scout, publisher and OpenClaw services are never modified here.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import sqlite3
import stat
import subprocess
import tempfile
from typing import Callable

RELEASE="v0.8.0-r4schedule1"
FORMAT="r4-proposal-schedule-v1"
HOME=Path.home()
UNIT_DIR=HOME/".config/systemd/user"
STATE=HOME/".local/state/bob-r4-schedule"
JOURNAL=STATE/"journal.json"
LOCK=STATE/"lock"
WORK_LOCK=STATE/"worker.lock"
SERVICE="bob-r4-propose.service"
TIMER="bob-r4-propose.timer"
R3_SERVICE="bob-r3-propose.service"
R3_TIMER="bob-r3-propose.timer"
PUBLISHER_SERVICE="bob-moltbook-publisher.service"
PUBLISHER_TIMER="bob-moltbook-publisher.timer"
SCOUT_TIMER="bob-moltbook-scout.timer"
SHADOW_SERVICE="bob-v08-shadow.service"
SHADOW_TIMER="bob-v08-shadow.timer"
UNITS=(SERVICE,TIMER,R3_SERVICE,R3_TIMER,PUBLISHER_SERVICE,
       PUBLISHER_TIMER,SCOUT_TIMER,SHADOW_SERVICE,SHADOW_TIMER)
ENABLED=frozenset(("enabled","enabled-runtime"))
PHASES=frozenset(("prepared","staged","enabling","enabled",
                   "disabling","disabled","recovering","rolled_back"))
UNIT_TEXT={
    SERVICE:"""[Unit]
Description=Bob R4 private proposal-only OpenClaw decision (no publisher)
After=openclaw-gateway.service
ConditionPathExists=%h/.config/moltbook/activity-queue.sqlite3

[Service]
Type=oneshot
ExecStart=%h/.local/bin/bob-r4-schedule --once
UMask=0077
TimeoutStartSec=180
NoNewPrivileges=yes
""",
    TIMER:"""[Unit]
Description=Bob R4 owner-approved, private proposal-only cadence

[Timer]
Unit=bob-r4-propose.service
OnActiveSec=120min
OnUnitInactiveSec=120min
RandomizedDelaySec=10min
AccuracySec=1min
Persistent=false

[Install]
WantedBy=timers.target
""",
}


@dataclass(frozen=True)
class Unit:
    load:str
    active:str
    enabled:str
    fragment:str
    dropins:str


def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def _owner()->bool:
    try:
        uid=os.geteuid()
        identity=pwd.getpwuid(uid)
        return (uid!=0 and identity.pw_name=="openclaw"
                and identity.pw_dir==str(HOME))
    except (OSError,KeyError,ValueError):
        return False


def _dir(path:Path,*,strict:bool=False)->bool:
    try:
        s=path.lstat()
        return (stat.S_ISDIR(s.st_mode) and s.st_uid==os.geteuid()
                and not s.st_mode&(0o077 if strict else 0o022))
    except OSError:
        return False


def _file(path:Path,*,max_bytes:int=16384)->bool:
    try:
        s=path.lstat()
        return (stat.S_ISREG(s.st_mode) and s.st_uid==os.geteuid()
                and s.st_nlink==1 and not s.st_mode&0o077
                and 0<s.st_size<=max_bytes)
    except OSError:
        return False


def _unit_dir_ok()->bool:
    return all(_dir(path) for path in
               (HOME,HOME/".config",HOME/".config/systemd",UNIT_DIR))


def _signed()->bool:
    try:
        from bob_r4_installed_gate import verify
        if not verify():
            return False
        path=HOME/".local/state/bob-updater/installed.json"
        if not _file(path,max_bytes=65536):
            return False
        registry=json.loads(path.read_text(encoding="utf-8"))
        required={"bob-r4-schedule","bob_r4_schedule.py","bob_r4_web.py"}
        return (registry.get("release")==RELEASE
                and required.issubset(registry.get("files",{})))
    except (OSError,TypeError,ValueError,KeyError,ImportError):
        return False


def _template_check()->bool:
    service,timer=UNIT_TEXT[SERVICE],UNIT_TEXT[TIMER]
    forbidden=("bob-moltbook-publisher", "moltbook.com", "curl ",
               "wget ", "Environment=", "ExecStartPre=", "ExecStartPost=",
               "OnBootSec=", "OnCalendar=", "Persistent=true",
               "Restart=always", "WantedBy=multi-user.target")
    return (set(UNIT_TEXT)=={SERVICE,TIMER}
            and service.count("ExecStart=")==1
            and "ExecStart=%h/.local/bin/bob-r4-schedule --once" in service
            and timer.count("Unit=")==1
            and "Unit="+SERVICE in timer
            and "OnActiveSec=120min" in timer
            and "OnUnitInactiveSec=120min" in timer
            and "RandomizedDelaySec=10min" in timer
            and "Persistent=false" in timer
            and all(0<len(s.encode())<=8192 and "\r" not in s
                    and "\x00" not in s and
                    not any(x in s for x in forbidden)
                    for s in UNIT_TEXT.values()))


def _probe(name:str,*,run=subprocess.run)->Unit:
    if name not in UNITS:
        raise ValueError("r4_schedule_unreviewed_unit")
    try:
        done=run(["systemctl","--user","show",name,"--no-pager",
                  "--property=LoadState,ActiveState,UnitFileState,FragmentPath,DropInPaths"],
                 capture_output=True,text=True,timeout=5,check=False)
        if done.returncode or not isinstance(done.stdout,str) or len(done.stdout)>2048:
            raise ValueError("r4_schedule_systemd_probe_failed")
        fields={}
        for line in done.stdout.splitlines():
            if line.count("=")!=1:
                continue
            key,val=line.split("=",1)
            if key not in ("LoadState","ActiveState","UnitFileState",
                           "FragmentPath","DropInPaths") or key in fields:
                raise ValueError("r4_schedule_systemd_shape")
            fields[key]=val
        if set(fields)!={"LoadState","ActiveState","UnitFileState",
                         "FragmentPath","DropInPaths"}:
            raise ValueError("r4_schedule_systemd_shape")
        return Unit(fields["LoadState"],fields["ActiveState"],
                    fields["UnitFileState"],fields["FragmentPath"],
                    fields["DropInPaths"])
    except (OSError,subprocess.TimeoutExpired):
        raise ValueError("r4_schedule_systemd_probe_failed") from None


def _states(probe=_probe)->dict[str,Unit]:
    return {unit:probe(unit) for unit in UNITS}


def _unit_ok(name:str,unit:Unit)->bool:
    if name not in UNIT_TEXT:
        return False
    f=UNIT_DIR/name
    return (unit.load=="loaded" and unit.fragment==str(f)
            and unit.dropins=="" and _file(f,max_bytes=8192)
            and f.read_bytes()==UNIT_TEXT[name].encode("utf-8"))


def _unit_absent(name:str,unit:Unit)->bool:
    p=UNIT_DIR/name
    return (unit.load=="not-found" and unit.active=="inactive"
            and unit.enabled=="not-found" and unit.fragment==""
            and unit.dropins=="" and not p.exists() and not p.is_symlink())


def _other_workers_idle(states:dict[str,Unit])->bool:
    if set(states)!=set(UNITS):
        return False
    for name in (R3_TIMER,PUBLISHER_TIMER,SCOUT_TIMER):
        unit=states[name]
        if (unit.load!="loaded" or unit.active!="active"
                or unit.enabled not in ENABLED or unit.dropins!=""):
            return False
    if any(states[name].active!="inactive" or states[name].dropins!=""
           for name in (R3_SERVICE,PUBLISHER_SERVICE,SHADOW_SERVICE)):
        return False
    shadow=states[SHADOW_TIMER]
    if (shadow.active!="inactive" or shadow.enabled in ENABLED
            or shadow.dropins!=""):
        return False
    return True


def _owner_modes_ready()->bool:
    """Read only: signed DB host, explicit Propose, global pause OFF."""
    try:
        from bob_publish_common import DB
        from bob_r313d_owner import trusted_manager_boundary
        from bob_r4_ledger import schema_ready
        from bob_r4_controls import read_modes,pause_state
        from bob_r4_agent import AVAILABLE
        if DB.is_symlink() or not DB.is_file():
            return False
        with closing(sqlite3.connect(
                DB.absolute().as_uri()+"?mode=ro",uri=True,timeout=4)) as db:
            db.execute("PRAGMA query_only=ON")
            if not trusted_manager_boundary(db) or not schema_ready(db):
                return False
            modes=read_modes(db)
            return not pause_state(db) and any(
                modes[action]=="propose" for action in AVAILABLE)
    except (OSError,sqlite3.Error,ValueError,KeyError,ImportError):
        return False


def _phase()->str:
    if JOURNAL.is_symlink():
        raise ValueError("r4_schedule_journal_symlink")
    if not JOURNAL.exists():
        return "absent"
    if not _file(JOURNAL):
        raise ValueError("r4_schedule_journal_untrusted")
    data=json.loads(JOURNAL.read_text(encoding="utf-8"))
    expected={name:_sha(body.encode()) for name,body in UNIT_TEXT.items()}
    if (type(data) is not dict or set(data)!={"format","release",
            "phase","units","public_send_authorized"}
            or data.get("format")!=FORMAT or data.get("release")!=RELEASE
            or data.get("phase") not in PHASES
            or data.get("units")!=expected
            or data.get("public_send_authorized") is not False):
        raise ValueError("r4_schedule_journal_untrusted")
    return data["phase"]


def _save(path:Path,raw:bytes):
    if path.exists() and path.is_symlink():
        raise ValueError("r4_schedule_symlink_destination")
    fd,temp=tempfile.mkstemp(prefix=".r4-sched-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            os.fchmod(out.fileno(),0o600)
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp,path)
        parent_fd=os.open(path.parent,os.O_DIRECTORY|os.O_RDONLY|os.O_NOFOLLOW)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        Path(temp).unlink(missing_ok=True)


def _write_phase(phase:str):
    if phase not in PHASES:
        raise ValueError("r4_schedule_phase_unreviewed")
    payload={"format":FORMAT,"release":RELEASE,"phase":phase,
             "public_send_authorized":False,
             "units":{name:_sha(body.encode()) for name,body in UNIT_TEXT.items()}}
    _save(JOURNAL,(json.dumps(payload,sort_keys=True)+"\n").encode())


def _lock(path:Path)->int:
    if not _dir(STATE,strict=True):
        raise ValueError("r4_schedule_state_not_private")
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    s=os.fstat(fd)
    if (not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid()
            or s.st_mode&0o077 or s.st_nlink!=1):
        os.close(fd)
        raise ValueError("r4_schedule_lock_untrusted")
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _ctl(args:tuple[str,...],*,run=subprocess.run):
    allowed={("daemon-reload",),("enable","--now",TIMER),
             ("disable","--now",TIMER)}
    if args not in allowed:
        raise ValueError("r4_schedule_unreviewed_systemd_command")
    try:
        p=run(["systemctl","--user",*args],
              text=True,capture_output=True,timeout=16,check=False)
        if p.returncode:
            raise ValueError("r4_schedule_systemd_command_failed")
    except (OSError,subprocess.TimeoutExpired):
        raise ValueError("r4_schedule_systemd_command_failed") from None


def _preflight_states(states:dict[str,Unit],phase:str)->tuple[bool,bool,list[str]]:
    """Pure state machine, does not inspect a mutable journal or trust CLI."""
    problems=[]
    if not _other_workers_idle(states):
        problems.append("scout_r3_or_publisher_topology_not_idle")
    if phase in ("absent","rolled_back"):
        if not all(_unit_absent(n,states[n]) for n in (SERVICE,TIMER)):
            problems.append("r4_unit_collision_or_unauthorized_stage")
        return not problems,False,problems
    if not all(_unit_ok(n,states[n]) for n in (SERVICE,TIMER)):
        problems.append("r4_unit_bytes_fragment_or_dropins_unverified")
    if states[SERVICE].active!="inactive":
        problems.append("r4_service_in_flight")
    if states[TIMER].active not in ("inactive","active"):
        problems.append("r4_timer_unknown")
    if phase in ("staged","disabled"):
        if (states[TIMER].active!="inactive" or
                states[TIMER].enabled in ENABLED):
            problems.append("r4_timer_unexpectedly_enabled")
        return False,not problems,problems
    if phase=="enabled":
        if (states[TIMER].active!="active" or
                states[TIMER].enabled not in ENABLED):
            problems.append("r4_timer_not_active_enabled")
        return False,False,problems
    problems.append("r4_incomplete_schedule_transaction")
    return False,False,problems


def inspect(*,probe=_probe,signed=_signed,modes=_owner_modes_ready)->dict:
    """Safe display for authenticated R4 dashboard and optional CLI check.

    It never reads model output, writes a file, invokes a worker, or touches
    the Moltbook API. Unknown evidence is an explicit blocker.
    """
    blockers=[]
    phase="unknown"
    state=None
    try:
        if not _owner():
            blockers.append("untrusted_account")
        if not _template_check():
            blockers.append("unreviewed_service_templates")
        if not signed():
            blockers.append("signed_r4_schedule_release_unverified")
        if not _unit_dir_ok():
            blockers.append("systemd_directory_untrusted")
        if STATE.exists() and not _dir(STATE,strict=True):
            blockers.append("schedule_state_directory_untrusted")
        phase=_phase()
        state=_states(probe)
        can_stage,can_enable,problems=_preflight_states(state,phase)
        blockers.extend(problems)
        mode_ok=bool(modes())
        if not mode_ok:
            blockers.append("r4_modes_off_or_paused")
        return {
            "format":"r4-schedule-status-v1",
            "release":RELEASE,
            "phase":phase,
            "timer_enabled":(phase=="enabled" and
                state[TIMER].active=="active" and
                state[TIMER].enabled in ENABLED and
                _unit_ok(TIMER,state[TIMER])),
            "worker_in_flight":state[SERVICE].active in ("active","activating"),
            "ready_to_stage":bool(can_stage and not blockers),
            "ready_to_enable":bool(can_enable and not blockers),
            "blockers":sorted(set(blockers)),
            "cadence":"120min_plus_0_to_10min_jitter_no_catchup",
            "public_dispatch_authorized":False,
            "database_modified_by_check":False,
            "service_modified_by_check":False,
        }
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error,ImportError):
        return {
            "format":"r4-schedule-status-v1",
            "release":RELEASE,"phase":"unknown",
            "timer_enabled":False,"worker_in_flight":False,
            "ready_to_stage":False,"ready_to_enable":False,
            "blockers":["schedule_read_only_evidence_unavailable"],
            "cadence":"120min_plus_0_to_10min_jitter_no_catchup",
            "public_dispatch_authorized":False,
            "database_modified_by_check":False,
            "service_modified_by_check":False,
        }


def _require_owner():
    if not _owner() or not _signed() or not _unit_dir_ok() or not _template_check():
        raise ValueError("r4_schedule_signed_owner_preflight_failed")


def stage(*,probe=_probe,control=_ctl)->str:
    """Explicit staged units, with timer DISABLED. No OpenClaw inference."""
    _require_owner()
    if STATE.is_symlink():
        raise ValueError("r4_schedule_existing_state_requires_review")
    existing=STATE.exists()
    if existing:
        if not _dir(STATE,strict=True) or _phase()!="rolled_back":
            raise ValueError("r4_schedule_existing_state_requires_review")
    before=_states(probe)
    safe,_,problems=_preflight_states(before,"absent")
    if not safe or problems:
        raise ValueError("r4_schedule_stage_topology_unverified")
    if not _owner_modes_ready():
        raise ValueError("r4_schedule_owner_modes_not_propose")
    if not existing:
        STATE.mkdir(mode=0o700,parents=True,exist_ok=False)
    fd=_lock(LOCK)
    try:
        _write_phase("prepared")
        try:
            for name,body in UNIT_TEXT.items():
                path=UNIT_DIR/name
                if path.exists() or path.is_symlink():
                    raise ValueError("r4_schedule_unit_collision")
                handle=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,
                               0o600)
                with os.fdopen(handle,"wb") as out:
                    out.write(body.encode())
                    out.flush()
                    os.fsync(out.fileno())
            control(("daemon-reload",))
            after=_states(probe)
            if (not all(_unit_ok(n,after[n]) for n in UNIT_TEXT)
                    or after[SERVICE].active!="inactive"
                    or after[TIMER].active!="inactive"
                    or after[TIMER].enabled in ENABLED):
                raise ValueError("r4_schedule_stage_postflight_failed")
            _write_phase("staged")
            return "staged_disabled"
        except (OSError,ValueError,subprocess.SubprocessError):
            # Recover only our exact owned bytes; unknown drift stays for
            # explicit inspection and never gets removed automatically.
            try:
                _remove_owned_units()
                control(("daemon-reload",))
                _write_phase("rolled_back")
                return "rolled_back"
            except (OSError,ValueError,subprocess.SubprocessError):
                raise ValueError("r4_schedule_stage_recovery_required") from None
    finally:
        os.close(fd)


def _remove_owned_units():
    for name,body in UNIT_TEXT.items():
        path=UNIT_DIR/name
        if path.is_symlink():
            raise ValueError("r4_schedule_unit_symlink")
        if path.exists():
            if not _file(path,max_bytes=8192) or path.read_bytes()!=body.encode():
                raise ValueError("r4_schedule_unit_drift")
            path.unlink()


def enable(*,probe=_probe,control=_ctl)->str:
    """Owner-approved enable; does not start R4 service or modify R3."""
    _require_owner()
    fd=_lock(LOCK)
    try:
        phase=_phase()
        if phase not in ("staged","disabled"):
            raise ValueError("r4_schedule_not_safely_staged")
        before=_states(probe)
        _,allowed,problems=_preflight_states(before,phase)
        if not allowed or problems or not _owner_modes_ready():
            raise ValueError("r4_schedule_enable_gate_refused")
        _write_phase("enabling")
        try:
            control(("enable","--now",TIMER))
            after=_states(probe)
            if (not _other_workers_idle(after)
                    or not all(_unit_ok(n,after[n]) for n in UNIT_TEXT)
                    or after[TIMER].active!="active"
                    or after[TIMER].enabled not in ENABLED
                    or after[SERVICE].active!="inactive"):
                raise ValueError("r4_schedule_enable_postflight_failed")
            _write_phase("enabled")
            return "enabled_private_proposals"
        except (OSError,ValueError,subprocess.SubprocessError):
            try:
                control(("disable","--now",TIMER))
                _write_phase("disabled")
                return "rolled_back_disabled"
            except (OSError,ValueError,subprocess.SubprocessError):
                raise ValueError("r4_schedule_enable_recovery_required") from None
    finally:
        os.close(fd)


def disable(*,probe=_probe,control=_ctl)->str:
    """Owner-only timer disable; does not terminate a running worker."""
    _require_owner()
    fd=_lock(LOCK)
    try:
        phase=_phase()
        if phase not in ("enabled","disabled","disabling"):
            raise ValueError("r4_schedule_disable_unknown_phase")
        states=_states(probe)
        if not all(_unit_ok(n,states[n]) for n in UNIT_TEXT):
            raise ValueError("r4_schedule_unit_drift")
        _write_phase("disabling")
        control(("disable","--now",TIMER))
        after=_states(probe)
        if after[TIMER].active!="inactive" or after[TIMER].enabled in ENABLED:
            raise ValueError("r4_schedule_timer_disable_unverified")
        _write_phase("disabled")
        return ("timer_disabled_worker_in_flight" if
                after[SERVICE].active in ("active","activating") else
                "timer_disabled")
    finally:
        os.close(fd)


def recover(*,probe=_probe,control=_ctl)->str:
    """Explicit reversible code/unit rollback only; never restore SQLite."""
    _require_owner()
    fd=_lock(LOCK)
    try:
        phase=_phase()
        if phase not in PHASES-{"rolled_back"}:
            raise ValueError("r4_schedule_no_recoverable_journal")
        before=_states(probe)
        if before[SERVICE].active!="inactive":
            raise ValueError("r4_schedule_worker_in_flight")
        # Unknown drop-ins/fragment paths cannot be disabled through these
        # commands. For interrupted prepared phases unit files may be absent.
        for name in UNIT_TEXT:
            s=before[name]
            if not (_unit_absent(name,s) or _unit_ok(name,s)):
                raise ValueError("r4_schedule_recovery_unit_drift")
        _write_phase("recovering")
        if _unit_ok(TIMER,before[TIMER]):
            control(("disable","--now",TIMER))
        _remove_owned_units()
        control(("daemon-reload",))
        final=_states(probe)
        if not all(_unit_absent(n,final[n]) for n in UNIT_TEXT):
            raise ValueError("r4_schedule_recovery_postflight_unverified")
        _write_phase("rolled_back")
        return "schedule_units_removed_no_data_restore"
    finally:
        os.close(fd)


def once(*,probe=_probe,signed=_signed,modes=_owner_modes_ready,
         worker:Callable|None=None)->dict:
    """One timer tick, no retries, and zero independent public authority."""
    from dataclasses import asdict
    empty={"status":"none","reason":"r4_schedule_guard_refused",
           "source_run":"","queued":False,"attempted":False,
           "dispatch_authorized":False}
    if not _owner() or not signed():
        return empty
    try:
        if _phase()!="enabled":
            return empty
        states=_states(probe)
        if (not _other_workers_idle(states)
                or not all(_unit_ok(n,states[n]) for n in UNIT_TEXT)
                or states[TIMER].active!="active"
                or states[TIMER].enabled not in ENABLED
                or not modes()):
            return empty
        fd=_lock(WORK_LOCK)
        try:
            if worker is None:
                from bob_r4_producer import run_one
                worker=run_one
            outcome=worker()
            result=asdict(outcome)
            if (type(result) is not dict or
                    set(result)!={"status","reason","source_run",
                                   "queued","attempted","dispatch_authorized"}
                    or any(result[k] is not False for k in
                           ("queued","attempted","dispatch_authorized"))
                    or result["status"] not in
                       ("none","skipped","proposed","refused")):
                return {**empty,"status":"refused",
                        "reason":"r4_schedule_result_unverified"}
            return result
        finally:
            os.close(fd)
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,
            ImportError,AttributeError,RuntimeError):
        return empty


def main(argv=None)->int:
    import sys
    args=sys.argv[1:] if argv is None else argv
    if args in (["--status"],["--check"]):
        report=inspect()
        print(json.dumps(report,sort_keys=True,separators=(",",":")))
        return 0 if args==["--status"] or (report["ready_to_stage"]
                     or report["ready_to_enable"]
                     or report["timer_enabled"]) else 1
    if args==["--once"]:
        report=once()
        print(json.dumps(report,sort_keys=True,separators=(",",":")))
        return 0 if report["status"] in ("none","skipped","proposed") else 1
    operations={
        "--stage":("STAGE R4 SCHEDULE",stage),
        "--enable":("ENABLE R4 SCHEDULE",enable),
        "--disable":("DISABLE R4 SCHEDULE",disable),
        "--recover":("RECOVER R4 SCHEDULE",recover),
    }
    if len(args)!=1 or args[0] not in operations:
        print("Usage: bob-r4-schedule --status|--check|--stage|--enable|--disable|--recover|--once")
        return 2
    phrase,operation=operations[args[0]]
    if not sys.stdin.isatty():
        print("BOB R4 SCHEDULE: refused (interactive owner approval required)")
        return 1
    try:
        answer=input("Type "+phrase+" to apply reviewed R4-only change: ")
        if answer!=phrase:
            print("BOB R4 SCHEDULE: no changes authorized")
            return 1
        outcome=operation()
        print("BOB R4 SCHEDULE: "+outcome)
        return 0 if outcome not in ("rolled_back","rolled_back_disabled") else 1
    except (OSError,ValueError,TypeError,sqlite3.Error,KeyError,
            subprocess.SubprocessError,RuntimeError):
        print("BOB R4 SCHEDULE: refused; inspect --status and private journal; no automatic retry")
        return 1


if __name__=="__main__":
    raise SystemExit(main())
