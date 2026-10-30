"""OC4 offline acceptance: evidence-only inactivity explanations and safe skips.

All synthetic data stays in temporary SQLite; no real Scout/OpenClaw/Moltbook
requests or posting and no host service mutations.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
import ast
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for p in ("src/lib/bob","src/bin","scripts","webui"):
    sys.path.insert(0,str(ROOT/p))
import bob_inactivity as inactivity
import bob_publish_common as common
import bob_overview as overview
import build_v076_oc4_candidate as builder
import build_v076_pubfix_handoff_candidate as prior

NOW=datetime(2026,10,30,16,30,tzinfo=timezone.utc)
RID1="20261030T155500Z"
RID2="20261030T155600Z"
RID3="20261030T155700Z"
RID4="20261030T155800Z"
DIGEST="f"*64
SECRET="UNTRUSTED_PRIVATE_BODIES"

def fixture(path):
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE publish_jobs(
          run_id TEXT PRIMARY KEY,approval_sha256 TEXT,mode TEXT,state TEXT,
          last_error TEXT,created_at TEXT,updated_at TEXT,attempted_at TEXT,
          comment_id TEXT,challenge_code TEXT,challenge_text TEXT,
          challenge_expires_at TEXT,verify_answer TEXT);
        CREATE TABLE decisions(run_id TEXT,draft_sha256 TEXT,status TEXT);
        CREATE TABLE publish_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,kind TEXT,details TEXT);
        """)
        items=[
          (RID1,"auto","failed","Human decision already exists",None,None),
          (RID2,"auto","failed","Human decision already exists",None,None),
          (RID3,"auto","failed","Human decision already exists",None,None),
          (RID4,"manual","queued",None,None,None),
        ]
        for rid,mode,state,error,attempted,comment_id in items:
            db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rid,DIGEST,mode,state,error,"2026-10-30T15:20:00+00:00",
                 "2026-10-30T16:15:00+00:00",attempted,comment_id,
                 None,None,None,None))
        for rid,status,digest in ((RID1,"approved",DIGEST),
                                  (RID2,"rejected",DIGEST),
                                  (RID3,"approved","0"*64)):
            db.execute("INSERT INTO decisions VALUES(?,?,?)",(rid,digest,status))
        db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
            ("2026-10-30T16:10:00+00:00","publisher_skip",
             "code=RATE_OR_BUDGET run="+RID4))
        db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
            ("2026-10-30T16:11:00+00:00","publisher_skip",
             "code=ALERT() run="+RID1))
        db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
            ("2026-10-30T16:12:00+00:00","publish_uncertain",
             SECRET+" -- Bearer token"))


def observed(*,auto=True,paused=False,manual=1,autos=0,originals=0):
    return {"paused":paused,
      "metrics":{"available":True,"auto_enabled":auto,
       "queues":{"comments_queued":manual+autos,"manual_queued":manual,
                 "auto_queued":autos,"originals_draft":0,"originals_queued":0,
                 "generation_queued":0},
       "usage":{"comments":2,"auto":0,"originals":originals},
       "limits":{"comment_daily":10,"comment_auto_daily":6,"original_daily":4},
       "next_possible_utc":{"comments":"2026-10-30T16:55:00+00:00"}},
      "operations":{"lanes":[
         {"key":"publisher","code":"RATE_LIMIT","state":"waiting",
          "next_scheduled":"Fri 2026-10-30 16:40:00 UTC","activity":"Waiting"},
         {"key":"scout","code":"NO_ACTIVE_SCOUT","state":"waiting",
          "updated_at":"2026-10-30T16:10:00+00:00",
          "activity":"Waiting for Scout timer"},
         {"key":"original","code":"MANUAL_ONLY","state":"idle",
          "activity":"Owner-requested"},
         {"key":"dependencies","code":"DEPENDENCIES_READY","state":"idle"}]}}

class InvestigatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"activity.sqlite3"
        fixture(self.path)

    def test_owner_decisions_are_distinguished_and_no_retry_claim(self):
        history=inactivity.read_private(self.path,at=NOW)
        self.assertTrue(history["available"])
        self.assertEqual(history["approved_blocked"],1)
        self.assertEqual(history["rejected_blocked"],1)
        self.assertEqual(history["undecided_blocked"],1)
        self.assertEqual(history["last_skip"]["code"],"RATE_OR_BUDGET")
        self.assertNotIn(SECRET,json.dumps(history))
        data=inactivity.explain(observed(),history,at=NOW)
        auto=next(x for x in data["sections"] if x["key"]=="auto")
        codes={r["code"] for r in auto["reasons"]}
        self.assertIn("AUTO_APPROVED_HANDOFF",codes)
        self.assertIn("AUTO_REJECTED",codes)
        self.assertIn("REVIEW_UNCONFIRMED",codes)
        self.assertNotIn(SECRET,json.dumps(data))
        self.assertIn("approval does not mean",data["notice"])
        self.assertEqual(data["scheduled_next"],"Fri 2026-10-30 16:40:00 UTC")
        self.assertEqual(data["policy_next"],"2026-10-30T16:55:00+00:00")
        comments=next(x for x in data["sections"] if x["key"]=="publisher")
        self.assertIn("RATE_LIMIT",{r["code"] for r in comments["reasons"]})
        self.assertIn("MANUAL_BACKLOG",{r["code"] for r in comments["reasons"]})

    def test_rejected_draft_is_not_misclassified_as_awaiting_approval(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE decisions SET status='rejected' WHERE run_id=?",(RID1,))
        history=inactivity.read_private(self.path,at=NOW)
        self.assertEqual(history["approved_blocked"],0)
        self.assertEqual(history["rejected_blocked"],2)
        auto=next(x for x in inactivity.explain(observed(),history,at=NOW)["sections"]
                  if x["key"]=="auto")
        self.assertNotIn("AUTO_APPROVED_HANDOFF",{r["code"] for r in auto["reasons"]})
        self.assertIn("AUTO_REJECTED",{r["code"] for r in auto["reasons"]})

    def test_bad_digest_unknown_and_attempted_never_claimed_recoverable(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_jobs SET challenge_code=? WHERE run_id=?",
                       ("moltbook_test",RID1))
        r=inactivity.read_private(self.path,at=NOW)
        self.assertEqual(r["approved_blocked"],0)
        self.assertEqual(r["undecided_blocked"],1)
        self.assertEqual(r["last_attempt"],"")

    def test_missing_or_corrupted_database_fails_closed(self):
        self.assertFalse(inactivity.read_private(self.path.parent/"none")["available"])
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TABLE decisions")
        r=inactivity.read_private(self.path,at=NOW)
        self.assertFalse(r["available"])
        d=inactivity.explain(observed(),r,at=NOW)
        reasons=d["sections"][0]["reasons"]
        self.assertIn("EVIDENCE_UNAVAILABLE",{x["code"] for x in reasons})

    def test_unknown_skip_never_leaks_and_throttle_is_deterministic(self):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
                ("2026-10-30T16:25:00+00:00","publisher_skip",
                 "code=NOT_A_REAL_CODE run="+RID4))
        r=inactivity.read_private(self.path,at=NOW)
        self.assertEqual(r["last_skip"]["code"],"RATE_OR_BUDGET")
        self.assertNotIn("NOT_A_REAL_CODE",json.dumps(r))
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_events SET details=? WHERE kind='publisher_skip'",
                       ("code="+SECRET+" run="+RID4,))
        self.assertIsNone(inactivity.read_private(self.path,at=NOW)["last_skip"])

    def test_no_original_post_does_not_indicate_a_failed_scheduled_job(self):
        h=inactivity.read_private(self.path,at=NOW)
        r=inactivity.explain(observed(originals=0),h,at=NOW)
        original=next(x for x in r["sections"] if x["key"]=="original")
        self.assertEqual(original["reasons"][0]["code"],"MANUAL_ONLY")
        self.assertIn("safety cap",original["reasons"][0]["detail"])

    def test_paused_or_no_telemetry_is_explicit(self):
        h=inactivity.read_private(self.path,at=NOW)
        pause=inactivity.explain(observed(paused=True),h,at=NOW)
        self.assertEqual(pause["sections"][0]["reasons"][0]["code"],"GLOBAL_PAUSE")
        empty=inactivity.explain({"metrics":{"available":False},
            "operations":{"lanes":[]}},inactivity._blank(),at=NOW)
        self.assertIn("EVIDENCE_UNAVAILABLE",
                      {x["code"] for x in empty["sections"][0]["reasons"]})

    def test_page_escapes_and_no_commands_or_mutating_forms(self):
        h=inactivity.read_private(self.path,at=NOW)
        r=inactivity.explain(observed(),h,at=NOW)
        r["sections"][0]["summary"]='<script>do_bad()</script>'
        html=inactivity.page(lambda title,body,route:body,data=r)
        self.assertIn("&lt;script&gt;do_bad()&lt;/script&gt;",html)
        self.assertNotIn("<script>do_bad()",html)
        self.assertNotIn("method=\"post\"",html.lower())
        self.assertIn("Why no activity?",html)
        self.assertIn("not scheduled",html)
        self.assertIn('/console',html)

    def test_manager_get_only_and_overview_link(self):
        old,oldnav=prior.build()
        new,nav=builder.build()
        self.assertIn(b'elif urlsplit(self.path).path == "/investigate":',new)
        self.assertIn(b'("/investigate", "Why no activity?",',nav)
        self.assertNotIn(b'("/investigate", "Why no activity?",',oldnav)
        def methods(data):
            tree=ast.parse(data)
            cls=next(c for c in tree.body if isinstance(c,ast.ClassDef)
                     and c.name=="Handler")
            return {x.name:ast.dump(x,include_attributes=False)
                    for x in cls.body if isinstance(x,ast.FunctionDef)}
        a,b=methods(old),methods(new)
        self.assertEqual(a["do_POST"],b["do_POST"])
        for name in ("_authenticated","_valid_host","_valid_origin",
                     "_handle_publication","_save_friend_scout"):
            self.assertEqual(a[name],b[name],name)
        self.assertIn('/investigate',overview._operations_html({
            "operations":{"headline":"Quiet","state":"waiting","detail":"",
              "checked_at":NOW.isoformat(),"lanes":[]}}))


class SkipInstrumentationTests(unittest.TestCase):
    def test_skip_events_throttled_and_never_include_private_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbpath=Path(tmp)/"activity.sqlite3"
            with sqlite3.connect(dbpath) as db:
                db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY,"
                           "at TEXT,kind TEXT,details TEXT)")
                script=ROOT/"src/bin/bob-moltbook-publisher"
                loader=importlib.machinery.SourceFileLoader("pub_telemetry_test",str(script))
                spec=importlib.util.spec_from_loader(loader.name,loader)
                pub=importlib.util.module_from_spec(spec)
                loader.exec_module(pub)
                pub.record_publisher_skip(db,"NO_QUEUE")
                pub.record_publisher_skip(db,"NO_QUEUE")
                pub.record_publisher_skip(db,"BOGUS",RID1)
                pub.record_publisher_skip(db,"GLOBAL_PAUSE",RID1)
                lines=db.execute("SELECT details FROM publish_events ORDER BY id").fetchall()
                self.assertEqual(len(lines),2)
                self.assertEqual(lines[0][0],"code=NO_QUEUE")
                self.assertEqual(lines[1][0],"code=GLOBAL_PAUSE run="+RID1)
                self.assertNotIn(SECRET,str(lines))
                self.assertNotIn("Bearer",str(lines))


if __name__=="__main__":
    unittest.main()
