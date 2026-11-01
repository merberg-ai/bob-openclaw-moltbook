#!/usr/bin/env python3
"""Consolidated R3 installed OFF-first acceptance: one read-only owner report.

A future owner may run this after an explicitly approved R3 cutover1 code
upgrade. It performs CA-verified authenticated HTTPS GETs of fixed local
manager routes, reads exact systemd unit metadata and readonly SQLite
schema/settings/counts, and inspects signed installed release file hashes.
It NEVER changes units, files, SQLite, owner rights or Moltbook activity.
No credential, private post IDs, drafts, command lines or environment values
are printed. This report is not proof of public publishing or WAN isolation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src"),
              str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import report_r38_effective_units as publisher
import r3_service_handoff as handoff
from bob_r313d_owner import schema_ready

DB=Path.home()/".config/moltbook/activity-queue.sqlite3"
STATES=frozenset(("queued","sending","uncertain","published","failed",
                  "verifying","verified_unconfirmed","awaiting_verification",
                  "verification_expired","needs_review","expired","cancelled"))
MAX_DB=256*1024*1024


def _owner() -> bool:
    try:
        who=pwd.getpwuid(os.geteuid())
        return (os.geteuid()!=0 and who.pw_name=="openclaw" and
                who.pw_dir==str(Path.home()))
    except (OSError,KeyError,ValueError):
        return False


def _db_review() -> dict:
    """Read-only no DDL, no contents/targets, exact OFF state."""
    result={"schema":"unverified","new_r3_owner_controls":"unverified",
            "attempted_jobs":None,"uncertain_jobs":None}
    if DB.is_symlink() or not DB.is_file() or DB.stat().st_size>MAX_DB:
        return result
    try:
        with sqlite3.connect(DB.absolute().as_uri()+"?mode=ro",
                             uri=True,timeout=3) as conn:
            conn.execute("PRAGMA query_only=ON")
            if not schema_ready(conn):
                return result
            settings=dict(conn.execute(
                "SELECT name,value FROM publish_settings WHERE name IN ("
                "'r3_comment_dial','r3_manual_enabled',"
                "'r3_auto_enabled','r3_auto_since')"))
            expected={"r3_comment_dial":"off","r3_manual_enabled":"0",
                      "r3_auto_enabled":"0","r3_auto_since":""}
            attempted=conn.execute(
                "SELECT COUNT(*) FROM publish_jobs WHERE attempted_at IS NOT NULL"
            ).fetchone()[0]
            uncertain=conn.execute(
                "SELECT COUNT(*) FROM publish_jobs WHERE state IN("
                "'sending','uncertain','verified_unconfirmed','verifying',"
                "'verification_failed')").fetchone()[0]
            if type(attempted) is not int or type(uncertain) is not int:
                return result
            result.update(schema="ready",
                new_r3_owner_controls=("default_off" if settings==expected
                                       else "requires_owner_review"),
                attempted_jobs=attempted, uncertain_jobs=uncertain)
    except (OSError,ValueError,sqlite3.Error,TypeError):
        pass
    return result


def _authenticated_r3_https() -> bool:
    """Reuse independently tested TLS acceptance, pinned CA and anon 401.

    The original CH-HTTPS3 checker verifies the immutable approved CA
    fingerprint, valid material, authenticated /r3, refusal of unauthenticated
    access and that plaintext HTTP is not served on the same port.
    Its low-level checks do NOT rely on the old installed release name.
    """
    try:
        import report_ch_https3_cutover as tls
        return (tls._ca_verified()
                and tls._authenticated_r3_https()
                and tls._plaintext_refused())
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,ImportError):
        return False


def _unit_gate(probe=handoff._snapshot) -> dict:
    """No shadow/proposal handoff yet; existing publisher remains one writer."""
    facts={name:probe(name) for name in handoff.EXACT_UNITS}
    base=handoff.assess(facts)
    return {
        "state": "preserved_legacy_timers" if not base else "review_required",
        "review_blockers":list(base),
        "publisher_timer_active": facts[handoff.PUBLISHER_TIMER].active=="active",
        "scout_timer_active":facts[handoff.SCOUT_TIMER].active=="active",
        "r3_proposal_timer_active":facts[handoff.TIMER].active=="active",
    }


def inspect(*,operator=_owner,installed=handoff._installed_cutover_off,
            health=None,route=_authenticated_r3_https,
            units=_unit_gate,dbreview=_db_review,
            publisher_report=publisher.report) -> dict:
    """All dependencies injectable in CI only; CLI uses fixed real checks."""
    result={
        "format":"bob-r3-offfirst-installed-acceptance-v1",
        "account":"unverified",
        "installed_signed_release":"unverified",
        "authenticated_https_health":"unverified",
        "authenticated_r3_controls":"unverified",
        "r3_owner_settings":"unverified",
        "single_existing_publisher":"unverified",
        "r3_proposal_timer":"unverified",
        "historical_attempts":None,
        "uncertain_delivery_rows":None,
        "acceptance":"NOT_VERIFIED",
        "wrote_files_or_database":False,
        "changed_systemd_or_publisher":False,
        "public_moltbook_requests":0,
        "r3_real_publishing_authorized":False,
        "external_duplicate_posting_excluded":False,
    }
    try:
        if not operator():
            return result
        result["account"]="verified"
        if not installed():
            return result
        result["installed_signed_release"]="cutover1_hard_off_verified"
        if health is None:
            authenticated=updater.healthy(
                updater.authorization(),release="v0.8.0-cutover1")
        else:
            authenticated=health()
        result["authenticated_https_health"]=(
            "PASS" if authenticated else "NOT_VERIFIED")
        result["authenticated_r3_controls"]=(
            "PASS" if route() else "NOT_VERIFIED")
        data=dbreview()
        result["r3_owner_settings"]=data.get("new_r3_owner_controls","unverified")
        result["historical_attempts"]=data.get("attempted_jobs")
        result["uncertain_delivery_rows"]=data.get("uncertain_jobs")
        shape=publisher_report()
        state=units()
        if (shape.get("effective_service")=="reviewed_shape"
                and shape.get("effective_timer")=="reviewed_shape"
                and not shape.get("review_blockers")
                and state.get("state")=="preserved_legacy_timers"):
            result["single_existing_publisher"]="PASS"
        result["r3_proposal_timer"]=(
            "OFF" if state.get("r3_proposal_timer_active") is False
            else "UNVERIFIED")
        if (result["authenticated_https_health"]=="PASS"
                and result["authenticated_r3_controls"]=="PASS"
                and data.get("schema")=="ready"
                and result["r3_owner_settings"]=="default_off"
                and result["single_existing_publisher"]=="PASS"
                and result["r3_proposal_timer"]=="OFF"
                and type(result["historical_attempts"]) is int
                and result["uncertain_delivery_rows"]==0):
            result["acceptance"]="PASS"
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,RuntimeError):
        return result
    return result


def main(args=None) -> int:
    argv=sys.argv[1:] if args is None else args
    if argv not in (["--postcheck"],["--postcheck","--json"]):
        print("Usage: python3 scripts/report_r3_cutover_installed.py "
              "--postcheck [--json]")
        return 2
    result=inspect()
    if "--json" in argv:
        print(json.dumps(result,indent=2,sort_keys=True))
    else:
        print("R3 CONSOLIDATED OFF-FIRST INSTALLED (READ ONLY)")
        for key in ("account","installed_signed_release",
                    "authenticated_https_health","authenticated_r3_controls",
                    "r3_owner_settings","single_existing_publisher",
                    "r3_proposal_timer","historical_attempts",
                    "uncertain_delivery_rows","acceptance"):
            print(key.replace("_"," ")+":",result[key])
        print("Database, credentials, public Moltbook or systemd changes: NO")
        print("R3 real public publishing authorized: NO")
    return 0 if result["acceptance"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
