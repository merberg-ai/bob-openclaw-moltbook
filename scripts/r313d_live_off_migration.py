#!/usr/bin/env python3
"""R3.13d explicit owner-controlled OFF-ONLY migration of fixed installed SQLite.

Default is READ ONLY. --apply-off requires normal WSL owner, verified R3
Off-first code release, matching updater registry, preserved R3 dispatch-Off
source, a private global pause marker, drained disabled publisher timer and
inactive publisher+manager services, a restore-tested PRIVATE SQLite backup,
an uncontended updater lock, and interactive EXACT confirmation.

DO NOT modify/revert the database on rollback. The existing publisher remains
the ONLY credentialed sender. No Moltbook HTTP, API key or owner enablement.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import pwd
import sqlite3
import stat
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src"/"lib"/"bob"),
              str(ROOT/"scripts")]

import bob_release_updater as updater
import report_r313d_host as stage_host
from backup_live_sqlite import create_verified_backup
from bob_v08.r313d_live_off_contract import (
    inspect_live_schema,_apply_off_transaction,
)

HOME=Path.home()
DB=HOME/".config/moltbook/activity-queue.sqlite3"
PAUSE=HOME/".config/bob-system/paused"
JOURNAL_DIR=HOME/".local/state/bob-r313d"
JOURNAL=JOURNAL_DIR/"migration-off.json"
SERVICES=("bob-moltbook-publisher.timer",
          "bob-moltbook-publisher.service",
          "bob-activity-manager.service")
STAGE_RELEASE="v0.8.0-r3stage1"


def _drained(*, probe=None) -> bool:
    """Read-only fixed-unit systemd checks, never an arbitrary unit name."""
    def installed(unit,command):
        if probe is not None:
            return probe(unit,command)
        completed=subprocess.run(
            ["systemctl","--user",command,unit],
            capture_output=True,text=True,timeout=5,check=False)
        return completed.stdout.strip()
    try:
        states=[installed(unit,"is-active") for unit in SERVICES]
        timer=installed(SERVICES[0],"is-enabled")
        return states==["inactive","inactive","inactive"] and (
            timer in ("disabled","masked"))
    except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):
        return False


def _paused() -> bool:
    try:
        row=PAUSE.lstat()
        return (stat.S_ISREG(row.st_mode) and row.st_uid==os.geteuid()
                and not row.st_mode & 0o077 and row.st_nlink==1)
    except OSError:
        return False


def _host_phase_accepted(evidence: dict, schema: dict, journal: str) -> bool:
    """Accept fixed private host in ONE of two exact, non-publishing phases.

    Private-copy eligibility is a *pre*-migration property, so demanding it
    after the additive R3 schema exists creates a false failure. Post-migrate
    trust requires schema=ready, journal=complete, explicit Off owner settings
    and exactly the additive-schema blocker, NO other boundary blockers.
    """
    try:
        host = evidence["host"]
        publisher = evidence["publisher"]
        if not (
            evidence["reviewed_off_gates"]["production_off_source"]
            and host["legacy_schema"] == "match"
            and publisher["effective_unit_shape"] == "reviewed_shape"
            and publisher["installed_file"] == "owner_controlled_regular"
            and publisher["updater_registry"] == "verified_registry_hash"
            and not publisher["review_blockers"]
        ):
            return False
        if schema["state"] == "eligible" and journal == "absent":
            return (
                host["private_copy_eligible"] is True
                and host["additive_schema"] == "absent"
                and host["r3_settings"] in ("absent_off", "explicit_off")
                and host["review_blockers"] == []
            )
        if schema["state"] == "ready" and journal == "complete":
            return (
                host["private_copy_eligible"] is False
                and host["additive_schema"] == "existing_needs_review"
                and host["r3_settings"] == "explicit_off"
                and host["review_blockers"] == ["additive_schema_not_empty"]
            )
    except (KeyError, TypeError, ValueError):
        pass
    return False


def _owner_installed_gate() -> bool:
    """Trust both verified pre-upgrade and committed post-upgrade Off states."""
    if os.geteuid() == 0 or pwd.getpwuid(os.geteuid()).pw_dir != str(HOME):
        return False
    evidence = stage_host.collect(private_copy=False)
    if not _host_phase_accepted(evidence, _db_review(), _journal_state()):
        return False
    try:
        record = updater.registry()
        return (
            record["release"] == STAGE_RELEASE
            and updater.live_ok(record)
            and "bob_r3_package.pyz" in record["files"]
            and "bob_r313d_owner.py" in record["files"]
            and "bob_r313d_web.py" in record["files"]
        )
    except (OSError, ValueError, TypeError, KeyError):
        return False


def _journal_state() -> str:
    if not JOURNAL.exists():
        return "absent"
    try:
        if JOURNAL.is_symlink() or JOURNAL.stat().st_size > 4096:
            return "untrusted"
        data=json.loads(JOURNAL.read_text(encoding="utf-8"))
        if (not isinstance(data,dict) or
                data.get("format")!="bob-r313d-off-migration-v1"
                or data.get("phase") not in ("prepared","complete")):
            return "untrusted"
        return data["phase"]
    except (OSError,UnicodeError,ValueError,TypeError):
        return "untrusted"


def _save_journal(phase: str) -> None:
    """Private atomic intent/complete marker, no database bytes or credentials."""
    if phase not in ("prepared","complete"):
        raise ValueError("unsupported_migration_journal_phase")
    if JOURNAL_DIR.is_symlink():
        raise ValueError("journal_directory_symlink")
    JOURNAL_DIR.mkdir(mode=0o700,parents=True,exist_ok=True)
    row=JOURNAL_DIR.lstat()
    if (not stat.S_ISDIR(row.st_mode) or row.st_uid!=os.geteuid()
            or row.st_mode & 0o077):
        raise ValueError("migration_journal_not_private")
    content=(json.dumps({
        "format":"bob-r313d-off-migration-v1",
        "phase":phase,
        "release":STAGE_RELEASE,
        "at":datetime.now(timezone.utc).isoformat(),
        "database_rollback_allowed":False,
        "r3_dispatch_authorized":False,
    },sort_keys=True)+"\n").encode("utf-8")
    fd,name=tempfile.mkstemp(prefix=".off-migrate-",dir=JOURNAL_DIR)
    tmp=Path(name)
    try:
        with os.fdopen(fd,"wb") as stream:
            os.fchmod(stream.fileno(),0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if JOURNAL.is_symlink():
            raise ValueError("migration_journal_symlink")
        os.replace(tmp,JOURNAL)
        dir_fd=os.open(JOURNAL_DIR,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        tmp.unlink(missing_ok=True)


def _db_review() -> dict:
    try:
        with closing(sqlite3.connect(DB.absolute().as_uri()+"?mode=ro",
                                     uri=True,timeout=6)) as db:
            db.execute("PRAGMA query_only=ON")
            return inspect_live_schema(db)
    except (OSError,ValueError,sqlite3.Error):
        return {"state":"refused","attempts":None,"uncertain":None}


def review() -> dict:
    installed=_owner_installed_gate()
    schema=_db_review()
    journal=_journal_state()
    return {
        "format":"bob-r313d-live-off-review-v1",
        "installed_off_first_release_verified":installed,
        "r3_schema":schema["state"],
        "historical_attempts":schema.get("attempts"),
        "historical_uncertain":schema.get("uncertain"),
        "publisher_and_manager_drained":_drained(),
        "global_pause":_paused(),
        "journal":journal,
        "eligible_for_off_migration":(
            installed and schema["state"]=="eligible" and
            journal=="absent" and _drained() and _paused()),
        "live_database_modified":False,
        "r3_dispatch_authorized":False,
        "canary_authorized":False,
    }


def _apply_off() -> dict:
    # No migration command supports alternate paths, unsigned flags, or root.
    gate=review()
    if not gate["eligible_for_off_migration"]:
        raise ValueError("reviewed_off_migration_gate_not_met")
    # Prevent a simultaneous bobctl updater transaction.
    lock_fd=updater.locked()
    try:
        if not review()["eligible_for_off_migration"]:
            raise ValueError("off_migration_boundary_changed")
        backup=create_verified_backup(DB,updater.BACKUP_DIR)
        if backup.get("integrity_check")!="ok" or (
                backup.get("restore_rehearsal")!="passed"):
            raise ValueError("restore_tested_backup_not_available")
        if not _drained() or not _paused():
            raise ValueError("publisher_state_changed_before_migration")
        _save_journal("prepared")
        with closing(sqlite3.connect(DB,timeout=10,isolation_level=None)) as db:
            # Assert the exact previously reviewed filename, no ATTACHed DB.
            rows=db.execute("PRAGMA database_list").fetchall()
            if (rows!=[(0,"main",str(DB))] and
                    not (len(rows)==2 and rows[0]==(0,"main",str(DB))
                         and rows[1][1]=="temp" and not rows[1][2])):
                raise ValueError("migration_database_attachment_or_path_changed")
            answer=_apply_off_transaction(db)
            if db.execute("PRAGMA quick_check(1)").fetchone()!=("ok",):
                raise RuntimeError("post_migration_integrity_needs_review")
        _save_journal("complete")
        return answer
    finally:
        os.close(lock_fd)


def main(argv=None) -> int:
    opts=sys.argv[1:] if argv is None else argv
    if opts not in ([],["--json"],["--apply-off"]):
        print("Usage: python3 scripts/r313d_live_off_migration.py "
              "[--json | --apply-off]")
        return 2
    if os.geteuid()==0:
        print("R3.13d OFF migration refused: do not use root")
        return 1
    try:
        if opts==["--apply-off"]:
            # TTY + exact user approval AFTER installed/service source checks.
            if not sys.stdin.isatty() or input(
                    "Type MIGRATE R3 OFF to back up and migrate the live SQLite "
                    "schema with R3 publishing still DISABLED: "
            )!="MIGRATE R3 OFF":
                raise ValueError("off_schema_migration_owner_confirmation_missing")
            out=_apply_off()
            print("R3.13d LIVE OFF SCHEMA: APPLIED (owner-confirmed)")
            print("historical attempts preserved:",out["historical_attempts_preserved"])
            print("historical uncertain preserved:",out["historical_uncertain_preserved"])
            print("database restore during rollback: NEVER")
            print("real R3 publication rights: NONE")
            print("publisher/manager services: STILL STOPPED")
            return 0
        out=review()
        if opts==["--json"]:
            print(json.dumps(out,sort_keys=True,indent=2))
        else:
            print("R3.13d FIXED-HOST OFF-ONLY MIGRATION (READ ONLY)")
            print("installed Off-first release:", "verified" if out[
                "installed_off_first_release_verified"] else "not_verified")
            print("schema:",out["r3_schema"])
            print("publisher and manager drained:",
                  "yes" if out["publisher_and_manager_drained"] else "no")
            print("private global pause:", "yes" if out["global_pause"] else "no")
            print("journal:",out["journal"])
            print("eligible for explicit migration:",
                  "yes" if out["eligible_for_off_migration"] else "no")
            print("live changes: NONE; public send authorization: NO")
        return 0
    except (OSError,ValueError,TypeError,sqlite3.Error,RuntimeError,
            subprocess.TimeoutExpired):
        print("R3.13d OFF migration: REFUSED; do not restore an older SQLite "
              "database or retry without inspecting migration journal")
        return 1


if __name__=="__main__":
    raise SystemExit(main())
