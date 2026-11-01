#!/usr/bin/env python3
"""R3 exact owner-approved canary source review. READ ONLY, NEVER a sender.

Runs against the already signed/installed R3 package and fixed private DB.
No user-selected paths, model outputs, public POSTs, approvals or queueing.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import r3_service_handoff as handoff

RUN="20261101T151033Z"
POST="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
RELEASE="v0.8.0-r3skip1"


def verdict(*, trusted: bool, manual: bool, automatic: bool,
            run: str, target: str, proposal_state: str,
            approval: tuple | None, seal: str,
            job: tuple | None, other_attempts: int,
            now: datetime) -> dict:
    """Pure, content-free assessment of already source-verified information."""
    answer={
        "source_run":RUN,
        "target_post":POST,
        "seal_sha256":None,
        "owner_approval_verified":False,
        "queue_state":"not_checked",
        "attempt_recorded":False,
        "canary_send_authorized":False,
        "next_gate":"STOP",
    }
    try:
        when=datetime.strptime(RUN,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if now.tzinfo is None or now.utcoffset() is None:
            return answer
        current=now.astimezone(timezone.utc)
        if not trusted or not manual or automatic or not (
                when <= current < when+timedelta(days=7)):
            return answer
        if run!=RUN or target!=POST or proposal_state!="proposed" or not (
                isinstance(seal,str) and len(seal)==64
                and all(c in "0123456789abcdef" for c in seal)):
            return answer
        if approval!=(seal,"approved") or other_attempts!=0:
            return answer
        answer["seal_sha256"]=seal
        answer["owner_approval_verified"]=True
        if job is None:
            answer["queue_state"]="none"
            answer["next_gate"]="REVIEW_EXACT_PIN_THEN_SEPARATELY_QUEUE"
        elif (len(job)==3 and job[0]=="queued" and job[1]=="manual"
              and job[2] is None):
            answer["queue_state"]="queued"
            answer["next_gate"]="REVIEW_EXACT_PIN_BEFORE_ANY_PUBLIC_ATTEMPT"
        else:
            answer["queue_state"]="other"
            answer["attempt_recorded"]=bool(len(job)==3 and job[2])
            answer["next_gate"]="STOP_AND_RECONCILE"
        return answer
    except (ValueError,TypeError,OverflowError):
        return answer


def inspect() -> dict:
    """Use checked-out source only as reader; installed signed code is authority."""
    from bob_r313d_package import load_verified
    from bob_publish_common import DATA,DB
    from bob_r313d_owner import (
        trusted_manager_boundary, control_state, _verified_proposal,
    )
    info=updater.registry()
    if (info["release"]!=RELEASE or not updater.live_ok(info)
            or updater.manager_transport(RELEASE)!="https"
            or not handoff._installed_cutover_off()
            or load_verified()!="verified_registry_archive"):
        raise ValueError("signed_offfirst_host_gate_refused")
    uri="file:"+quote(str(DB),safe="/")+"?mode=ro"
    with closing(sqlite3.connect(uri,uri=True,isolation_level=None,timeout=5)) as db:
        db.execute("PRAGMA query_only=ON")
        if not trusted_manager_boundary(db):
            raise ValueError("untrusted_private_source_database")
        state=control_state(db)
        if state.get("schema")!="ready":
            raise ValueError("schema_not_ready")
        action, _, seal, proposal_state=_verified_proposal(db,DATA,RUN)
        approval=db.execute(
            "SELECT seal_sha256,decision FROM r3_owner_approvals "
            "WHERE source_run=?",(RUN,)).fetchone()
        job=db.execute(
            "SELECT state,mode,attempted_at FROM publish_jobs "
            "WHERE run_id=?",(RUN,)).fetchone()
        others=db.execute(
            "SELECT COUNT(*) FROM publish_jobs "
            "WHERE post_id=? AND run_id<>? AND attempted_at IS NOT NULL",
            (POST,RUN)).fetchone()[0]
        return verdict(
            trusted=True,manual=state["manual"],automatic=state["automatic"],
            run=action.source_run,target=action.target_id,
            proposal_state=proposal_state,approval=approval,seal=seal,
            job=job,other_attempts=others,now=datetime.now(timezone.utc))


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r3_canary_approved.py --check")
        return 2
    try:
        result=inspect()
    except (OSError,KeyError,TypeError,ValueError,sqlite3.Error,ImportError):
        result={"source_run":RUN,"target_post":POST,"seal_sha256":None,
                "owner_approval_verified":False,"canary_send_authorized":False,
                "next_gate":"STOP_AND_REVIEW_HOST_OR_SOURCE"}
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0 if result["owner_approval_verified"] and (
        result["next_gate"] in (
            "REVIEW_EXACT_PIN_THEN_SEPARATELY_QUEUE",
            "REVIEW_EXACT_PIN_BEFORE_ANY_PUBLIC_ATTEMPT")) else 1


if __name__=="__main__":
    raise SystemExit(main())
