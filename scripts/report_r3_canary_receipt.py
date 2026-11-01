#!/usr/bin/env python3
"""R3 exact one-comment canary receipt reconciliation, READ ONLY.

Never publishes, loads Moltbook credentials, or marks uncertain as failed.
An API acknowledgment is NOT independent confirmation of public visibility.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]
import audit_comment_visibility as visible

RUN="20261101T151033Z"
POST="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"


def report(*, public_get=False, auditor=None, _synthetic_db=None):
    from bob_publish_common import DB
    # An in-process offline test may inject a private synthetic fixture.
    # The CLI does not expose paths and always reads the fixed real queue.
    db_path=Path(_synthetic_db) if _synthetic_db is not None else DB
    uri="file:"+quote(str(db_path),safe="/")+"?mode=ro"
    def one():
        with closing(sqlite3.connect(uri,uri=True,isolation_level=None,timeout=4)) as db:
            db.execute("PRAGMA query_only=ON")
            job=db.execute(
                "SELECT post_id,mode,state,attempted_at,comment_id "
                "FROM publish_jobs WHERE run_id=?",(RUN,)).fetchone()
            other=db.execute(
                "SELECT COUNT(*) FROM publish_jobs WHERE post_id=? "
                "AND run_id<>? AND attempted_at IS NOT NULL",
                (POST,RUN)).fetchone()[0]
        return job,other
    first=one()
    job,other=first
    state=job[2] if job else "not_queued"
    attempted=bool(job and job[3])
    comment=job[4] if job else None
    trusted=bool(job and job[0]==POST and job[1]=="manual")
    observation="not_requested"
    if public_get:
        if (trusted and attempted and isinstance(comment,str)
                and visible.UUID.fullmatch(comment)):
            provider=auditor if callable(auditor) else visible.audit_one
            observation=provider(POST,comment,max_pages=2)
            if observation not in (
                    "visible_in_public_listing","not_observed_in_public_listing",
                    "scan_incomplete","public_check_unavailable","id_unconfirmed"):
                observation="public_check_unavailable"
        else:
            observation="id_unconfirmed"
    second=one()
    stable=first==second
    independently_visible=(
        public_get and stable and trusted and attempted and other==0
        and observation=="visible_in_public_listing")
    return {"source_run":RUN,"target_post":POST,
            "state":state,"attempt_recorded":attempted,
            "saved_comment_id":comment if (
                isinstance(comment,str) and visible.UUID.fullmatch(comment)) else None,
            "no_other_attempted_target":other==0,
            "local_record_stable":stable,
            "public_observation":observation,
            "independently_visible":bool(independently_visible),
            "api_ack_is_public_receipt":False,
            "external_duplicate_excluded":False,
            "retry_authorized":False,
            "db_or_publisher_changed_by_report":False}


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args not in (["--check"],["--public-get"]):
        print("Usage: python3 scripts/report_r3_canary_receipt.py [--check|--public-get]")
        return 2
    try:
        result=report(public_get=args==["--public-get"])
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,
            TimeoutError,UnicodeError):
        result={"source_run":RUN,"target_post":POST,
                "state":"unavailable","independently_visible":False,
                "retry_authorized":False}
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0 if result["state"]!="unavailable" else 1


if __name__=="__main__":
    raise SystemExit(main())
