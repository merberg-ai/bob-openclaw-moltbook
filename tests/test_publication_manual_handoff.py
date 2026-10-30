"""Publication recovery: approving auto must allow ONE explicit manual handoff.

The tests use private temporary SQLite, validated synthetic saved Scout files,
and mocked network calls. Nothing touches a live Bob or Moltbook.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import ast
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for path in ("src/lib/bob","src/bin","scripts","webui"):
    sys.path.insert(0,str(ROOT/path))
import bob_publish_common as common
import build_v076_oc3_candidate as prior
import build_v076_pubfix_handoff_candidate as builder

PID="01234567-89ab-cdef-0123-456789abcdef"
RID=datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")


def publisher():
    loader=importlib.machinery.SourceFileLoader(
        "test_pubfix_bob_publisher",str(ROOT/"src/bin/bob-moltbook-publisher"))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    obj=importlib.util.module_from_spec(spec)
    loader.exec_module(obj)
    return obj


class PublicationHandoffTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        for key,value in (("DATA",self.root),
                          ("DB",self.root/"activity-queue.sqlite3")):
            p=patch.object(common,key,value)
            p.start()
            self.addCleanup(p.stop)
        with common.connect():
            pass
        self.record=self.make_record()

    def make_record(self):
        payload={"posts":[{"id":PID,"title":"Safety discussion",
                           "content":"Talk about open source tools.",
                           "author":"PublicAgent"}]}
        raw=json.dumps(payload).encode()
        (self.root/("scout-feed-"+RID+".json")).write_bytes(raw)
        sha=hashlib.sha256(raw).hexdigest()
        draft="I find this relevant. Could you explain the tradeoffs?"
        record={"schema":2,"run_id":RID,"status":"pending",
                "chosen_post_id":PID,"chosen_title":"Safety discussion",
                "chosen_author":"PublicAgent","draft_comment":draft,
                "draft_sha256":hashlib.sha256(draft.encode()).hexdigest(),
                "snapshot_sha256":sha,"snapshot_file":"scout-feed-"+RID+".json",
                "approval_sha256":hashlib.sha256((PID+"\n"+draft+"\n"+sha).encode()).hexdigest()}
        (self.root/("scout-result-"+RID+".json")).write_text(json.dumps(record))
        self.assertIsNotNone(common.load_record(RID))
        return record

    def approve(self,db,status="approved",digest=None):
        db.execute("INSERT OR REPLACE INTO decisions(run_id,draft_sha256,status,decided_at)"
                   "VALUES(?,?,?,?)",(RID,digest or self.record["approval_sha256"],
                                     status,common.now()))

    def existing(self,db,*,mode="auto",state="queued",error=None,attempted=None,
                 comment=None,code=None,answer=None,sha=None,pid=PID,draft=None,
                 challenge=None,expiry=None):
        db.execute("INSERT INTO publish_jobs(run_id,approval_sha256,post_id,draft_comment,"
                   "mode,state,created_at,attempted_at,comment_id,challenge_code,"
                   "challenge_text,challenge_expires_at,verify_answer,last_error,updated_at)"
                   "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (RID,sha or self.record["approval_sha256"],pid,
                    self.record["draft_comment"] if draft is None else draft,
                    mode,state,common.now(),attempted,comment,code,challenge,expiry,
                    answer,error,common.now()))

    def state(self,db):
        return db.execute("SELECT mode,state,attempted_at,last_error FROM publish_jobs "
                          "WHERE run_id=?",(RID,)).fetchone()

    def test_approve_before_auto_send_can_be_explicitly_queued_as_manual(self):
        with common.connect() as db:
            self.existing(db)
            self.approve(db)
            self.assertTrue(common.manual_recovery_allowed(db,RID))
            common.queue_manual(db,RID)
            self.assertEqual(self.state(db),("manual","queued",None,None))
            self.assertFalse(common.manual_recovery_allowed(db,RID))
            self.assertEqual(db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0],1)
            with self.assertRaisesRegex(ValueError,"already has a publication attempt"):
                common.queue_manual(db,RID)
            self.assertEqual(db.execute("SELECT kind FROM publish_events").fetchone()[0],
                             "publish_manual_handoff")

    def test_historical_blocked_auto_review_can_be_recovered_without_a_send(self):
        for reason in sorted(common.AUTO_REVIEW_ONLY_FAILURES):
            with self.subTest(reason=reason),common.connect() as db:
                db.execute("DELETE FROM publish_jobs")
                db.execute("DELETE FROM publish_events")
                self.existing(db,state="failed",error=reason)
                self.approve(db)
                self.assertTrue(common.manual_recovery_allowed(db,RID))
                common.queue_manual(db,RID)
                self.assertEqual(self.state(db),("manual","queued",None,None))

    def test_existing_no_auto_job_manual_queue_still_works(self):
        with common.connect() as db:
            self.approve(db)
            common.queue_manual(db,RID)
            self.assertEqual(self.state(db),("manual","queued",None,None))
            self.assertEqual(db.execute("SELECT kind FROM publish_events").fetchone()[0],
                             "publish_queued")

    def test_rejected_or_changed_approval_always_blocks(self):
        with common.connect() as db:
            self.existing(db,state="failed",error="Human decision already exists")
            self.approve(db,"rejected")
            self.assertFalse(common.manual_recovery_allowed(db,RID))
            with self.assertRaisesRegex(ValueError,"approved"):
                common.queue_manual(db,RID)
            self.approve(db,digest="0"*64)
            self.assertFalse(common.manual_recovery_allowed(db,RID))
            with self.assertRaisesRegex(ValueError,"approved"):
                common.queue_manual(db,RID)
            self.assertEqual(self.state(db),("auto","failed",None,"Human decision already exists"))

    def test_uncertain_sent_duplicate_or_unsafe_failed_reason_never_promoted(self):
        cases=[
            dict(state="sending",attempted=common.now()),
            dict(state="uncertain",attempted=common.now()),
            dict(state="published",attempted=common.now(),comment=PID),
            dict(state="awaiting_verification",code="moltbook_hello"),
            dict(state="verification_failed",attempted=common.now()),
            dict(state="failed",error="Integrity validation failed"),
            dict(state="failed",error="Draft expired"),
            dict(state="queued",attempted=common.now()),
            dict(state="queued",comment=PID),
            dict(state="queued",code="moltbook_hello"),
            dict(state="queued",challenge="answer me"),
            dict(state="queued",expiry="tomorrow"),
            dict(state="queued",answer="3.00"),
            dict(state="queued",sha="1"*64),
            dict(state="queued",pid="11111111-2222-3333-4444-555555555555"),
            dict(state="queued",draft="tampered"),
        ]
        for i,case in enumerate(cases):
            with self.subTest(i=i),common.connect() as db:
                db.execute("DELETE FROM publish_jobs")
                db.execute("DELETE FROM publish_events")
                self.existing(db,**case)
                self.approve(db)
                self.assertFalse(common.manual_recovery_allowed(db,RID))
                with self.assertRaisesRegex(ValueError,"already has a publication attempt"):
                    common.queue_manual(db,RID)
                self.assertEqual(db.execute(
                    "SELECT mode FROM publish_jobs WHERE run_id=?",(RID,)).fetchone()[0],"auto")

    def test_cannot_recover_if_saved_snapshot_is_tampered(self):
        with common.connect() as db:
            self.existing(db,state="failed",error="Human decision already exists")
            self.approve(db)
            (self.root/("scout-feed-"+RID+".json")).write_text('{"posts":[]}')
            self.assertFalse(common.manual_recovery_allowed(db,RID))
            with self.assertRaisesRegex(ValueError,"Invalid or changed scouting record"):
                common.queue_manual(db,RID)

    def test_stale_automatic_selection_does_not_send_after_owner_handoff(self):
        worker=publisher()
        with common.connect() as db:
            self.existing(db)
            common.set_setting(db,"auto_enabled","1")
        emitted=[]
        def get_then_approve(method,path,*args,**kwargs):
            emitted.append(method)
            if method=="POST":
                raise AssertionError("Stale automatic worker must never send")
            with common.connect() as other:
                self.approve(other)
                common.queue_manual(other,RID)
            return {"post":{"id":PID}}
        with common.connect() as db, \
            patch.object(worker,"auto_candidates",return_value=0), \
            patch.object(worker,"allow_auto_candidate",return_value=True), \
            patch.object(worker,"checkpoint"), \
            patch.object(worker,"can_send",return_value=(True,"")), \
            patch.object(worker,"api",side_effect=get_then_approve):
            msg=worker.publisher_step(db)
        self.assertIn("changed; not sent",msg)
        self.assertEqual(emitted,["GET"])
        with common.connect() as db:
            self.assertEqual(self.state(db),("manual","queued",None,None))
            self.assertEqual(db.execute("SELECT count(*) FROM publish_events "
                                        "WHERE kind='publish_attempt'").fetchone()[0],0)

    def test_existing_manual_publisher_path_claims_one_send(self):
        worker=publisher()
        with common.connect() as db:
            self.approve(db)
            common.queue_manual(db,RID)
        requests=[]
        def stub(method,path,*args,**kwargs):
            requests.append(method)
            if method=="GET":
                return {"post":{"id":PID}}
            return {"success":True,"comment":{"id":"11111111-2222-3333-4444-555555555555"}}
        with common.connect() as db, \
            patch.object(worker,"auto_candidates",return_value=0), \
            patch.object(worker,"checkpoint"), \
            patch.object(worker,"can_send",return_value=(True,"")), \
            patch.object(worker,"api",side_effect=stub), \
            patch.object(worker,"api_key",return_value="fake-key"):
            result=worker.publisher_step(db)
        self.assertIn("published",result)
        self.assertEqual(requests,["GET","POST"])
        with common.connect() as db:
            row=db.execute("SELECT mode,state,attempted_at FROM publish_jobs WHERE run_id=?",(RID,)).fetchone()
            self.assertEqual(row[:2],("manual","published"))
            self.assertIsNotNone(row[2])

    def test_manager_only_changes_readonly_render_no_post_handlers(self):
        old,oldnav=prior.build()
        new,newnav=builder.build()
        self.assertEqual(oldnav,newnav)
        self.assertIn(b"manual_recovery_allowed",new)
        self.assertIn(b"Queue approved draft manually",new)
        self.assertIn(b"stamp in recoverable",new)
        def methods(source):
            tree=ast.parse(source)
            cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="Handler")
            return {x.name:ast.dump(x,include_attributes=False)
                    for x in cls.body if isinstance(x,ast.FunctionDef)}
        a,b=methods(old),methods(new)
        for method in a:
            self.assertEqual(a[method],b[method],method)
        self.assertIn(b"f'<form method=\"post\" action=\"/publish/{stamp}\">'",new)


if __name__=="__main__":
    unittest.main()
