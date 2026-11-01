"""Bounded simulation of R4 preflight/final barrier and receipt semantics.

These tests use no Moltbook credentials or network and cannot mutate Bob's
persistent queue. All synthetic network values are injected callbacks.
"""
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src/lib/bob")]
from bob_v08.evidence import read_observation
from bob_v08.r39_publisher_review import RemoteReview
from bob_r4_decision import Decision
import bob_r4_ledger as ledger
import bob_r4_suggestions as suggestions
import bob_r4_outbox as outbox
import bob_r4_remote_gate as remote
import bob_r4_verified_send_lab as lab
import bob_r4_publisher_adapter as adapter
import bob_publish_common as common
from unittest.mock import patch

RUN="20261101T151033Z"
POST="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
AUTHOR="Other_Agent"
SELF="Bob"
NOW=datetime(2026,11,1,16,20,tzinfo=timezone.utc)


class R4VerifiedPostTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="r4-verified-remote-")
        self.addCleanup(t.cleanup)
        self.data=Path(t.name)
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT);
          CREATE TABLE publish_events(id INTEGER PRIMARY KEY,at TEXT,
            kind TEXT,details TEXT);
          CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,post_id TEXT,
            attempted_at TEXT,state TEXT);
          CREATE TABLE r3_proposals(source_run TEXT PRIMARY KEY,post_id TEXT);
        """)
        ledger.initialize(self.db)
        suggestions.initialize(self.db)
        outbox.initialize(self.db)
        self.db.execute("INSERT INTO publish_settings VALUES('r4_mode_upvote','propose')")
        self.db.execute("INSERT INTO publish_settings VALUES('r4_global_pause','0')")
        self.make_scout(AUTHOR)
        self.approve_and_queue()
        self.calls=[]
        self.tick=NOW
        self.posts=0
        self.gets=0
        self.self_gets=0
        self.paused=False

    def make_scout(self,author):
        feed=json.dumps({"posts":[{"id":POST,"author":author,
            "title":"A discussion on review gates",
            "content":"Synthetic only"}]},sort_keys=True).encode()
        digest=hashlib.sha256(feed).hexdigest()
        draft="Synthetic legacy draft unused by R4"
        result=dict(schema=2,run_id=RUN,
                    snapshot_file="scout-feed-"+RUN+".json",
                    snapshot_sha256=digest,
                    chosen_post_id=POST,chosen_author=author,
                    chosen_title="A discussion on review gates",
                    draft_comment=draft,status="pending",
                    draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),
                    approval_sha256=hashlib.sha256(
                        (POST+"\n"+draft+"\n"+digest).encode()).hexdigest())
        (self.data/("scout-feed-"+RUN+".json")).write_bytes(feed)
        (self.data/("scout-result-"+RUN+".json")).write_text(
            json.dumps(result))
        self.observed=read_observation(self.data,RUN)

    def approve_and_queue(self):
        decision=Decision("upvote",RUN,POST,"A useful perspective to retain",
                          "","","","")
        ledger.record(self.db,self.data,self.observed,decision,at=NOW)
        seal=ledger.recent(self.db,self.data)[0]["seal"]
        ledger.review(self.db,self.data,RUN,seal,"approve",
                      "APPROVE R4 "+RUN,trusted=True,at=NOW)
        self.seal=seal
        outbox.queue(self.db,self.data,RUN,seal,"QUEUE R4 UPVOTE "+RUN,
                     trusted=True,at=NOW)

    def clock(self):
        return self.tick

    def get_post(self,post,author):
        self.gets+=1
        self.calls.append(("GET_POST",post,author))
        return RemoteReview(post==POST and author==AUTHOR,
                            "target_and_author_match")

    def me(self):
        self.self_gets+=1
        self.calls.append(("GET_ME",SELF))
        return {"success":True,"agent":{"name":SELF}}

    def post(self,method,path):
        self.posts+=1
        self.calls.append((method,path))
        self.assertEqual(method,"POST")
        self.assertEqual(path,"/posts/"+POST+"/upvote")
        row=self.db.execute(
            "SELECT state,attempted_at FROM r4_action_outbox "
            "WHERE source_run=?",(RUN,)).fetchone()
        self.assertEqual(row[0],"attempting")
        self.assertTrue(row[1])
        return {"success":True,"message":"Upvoted!"}

    def exercise(self):
        return lab.simulate_verified_attempt(
            self.db,self.data,clock=self.clock,
            post_get=self.get_post,self_get=self.me,
            post_call=self.post,global_pause=lambda:self.paused)

    def test_two_remote_gets_and_counted_intent_before_single_fake_post(self):
        self.assertEqual(self.exercise(),"acknowledged")
        self.assertEqual((self.gets,self.self_gets,self.posts),(2,2,1))
        self.assertTrue(self.calls.index(("POST","/posts/"+POST+"/upvote"))>3)
        self.assertEqual(self.db.execute(
            "SELECT state FROM r4_action_outbox").fetchone(),
            ("acknowledged",))
        self.assertEqual(self.exercise(),"no_queued_r4_action")
        self.assertEqual(self.posts,1)

    def test_self_identity_cannot_be_inferred_from_saved_local_friend(self):
        self.me=lambda:{"success":True,"agent":{"name":AUTHOR}}
        self.assertEqual(self.exercise(),"remote_or_owner_preflight_refused")
        self.assertEqual(self.posts,0)
        self.assertEqual(self.db.execute(
            "SELECT state,attempted_at FROM r4_action_outbox").fetchone(),
            ("queued",None))

    def test_profile_must_be_successful_exact_authenticated_shape(self):
        for value in ({}, {"success":True,"agent":{"name":"Bob"}},
                      {"success":"true","agent":{"name":SELF}},
                      {"success":True,"agent":{"name":"../../Bob"}},
                      {"success":False,"agent":{"name":SELF}},
                      {"success":True,"data":{"agent":{"name":"Bob"}}}):
            with self.subTest(value=value):
                result=remote.agent_identity(value)
                self.assertEqual(result.verified,
                                 value in (
                                     {"success":True,"agent":{"name":"Bob"}},
                                     {"success":True,"data":{"agent":{"name":"Bob"}}}
                                 ))

    def test_remote_identity_mismatch_or_deleted_or_unavailable_refused(self):
        self.get_post=lambda *a:RemoteReview(False,"target_deleted")
        self.assertEqual(self.exercise(),"remote_or_owner_preflight_refused")
        self.assertEqual(self.posts,0)
        self.assertEqual(self.db.execute(
            "SELECT attempted_at FROM r4_action_outbox").fetchone(),(None,))

    def test_post_intent_remote_author_drift_consumes_once_no_send(self):
        first=self.get_post
        def change(post,author):
            if self.gets:
                return RemoteReview(False,"author_identity_mismatch")
            return first(post,author)
        self.get_post=change
        self.assertEqual(self.exercise(),"uncertain")
        self.assertEqual(self.posts,0)
        self.assertEqual(self.db.execute(
            "SELECT state,attempted_at FROM r4_action_outbox").fetchone()[0],
            "uncertain")
        self.assertEqual(self.exercise(),"no_queued_r4_action")

    def test_late_global_pause_consumes_counted_intent_without_post(self):
        original=self.me
        def pause_after_first_profile():
            answer=original()
            if self.self_gets==1:
                self.paused=True
            return answer
        self.me=pause_after_first_profile
        self.assertEqual(self.exercise(),"held_global_pause")
        self.assertEqual(self.posts,0)
        self.assertEqual(self.db.execute(
            "SELECT attempted_at FROM r4_action_outbox").fetchone(),(None,))

    def test_global_pause_after_intent_in_second_get_no_public_post(self):
        original=self.me
        def pause_second():
            answer=original()
            if self.self_gets==2:
                self.paused=True
            return answer
        self.me=pause_second
        self.assertEqual(self.exercise(),"uncertain")
        self.assertEqual(self.posts,0)
        self.assertEqual(self.db.execute(
            "SELECT state FROM r4_action_outbox").fetchone(),("uncertain",))

    def test_malformed_api_ack_or_timeout_is_uncertain_no_replay(self):
        for payload in ({"ok":True},{"success":False},
                        {"success":"true"},{"success":True,"error":"boom"}):
            self.assertFalse(remote.upvote_ack(payload))
        self.post=lambda method,path:(_ for _ in ()).throw(TimeoutError())
        self.assertEqual(self.exercise(),"uncertain")
        self.assertEqual(self.exercise(),"no_queued_r4_action")

    def test_stale_second_get_clock_consumes_once_but_sends_nothing(self):
        first=self.me
        def delayed():
            result=first()
            if self.self_gets==2:
                self.tick+=timedelta(minutes=3)
            return result
        self.me=delayed
        self.assertEqual(self.exercise(),"uncertain")
        self.assertEqual(self.posts,0)

    def test_crash_recovery_with_no_second_public_attempt(self):
        outbox.reserve_once(self.db,self.data,at=NOW)
        self.assertEqual(self.exercise(),"recovered_uncertain_no_replay")
        self.assertEqual(self.exercise(),"no_queued_r4_action")
        self.assertEqual(self.posts,0)

    def test_late_legacy_attempt_during_remote_get_blocks_counted_claim(self):
        first=self.get_post
        def create_competing_attempt(post,author):
            answer=first(post,author)
            if self.gets==1:
                self.db.execute(
                    "INSERT INTO publish_jobs VALUES(?,?,?,?)",
                    ("20261101T161900Z",
                     "a9ccf436-c5d5-4849-af92-843670ab8271",
                     (NOW-timedelta(minutes=1)).isoformat(),"published"))
            return answer
        self.get_post=create_competing_attempt
        self.assertEqual(self.exercise(),"private_claim_refused_no_send")
        self.assertEqual(self.posts,0)
        self.assertEqual(self.db.execute(
            "SELECT state,attempted_at FROM r4_action_outbox").fetchone(),
            ("queued",None))

    def test_self_identity_changed_after_counted_claim_never_posts(self):
        original=self.me
        def second_identity():
            answer=original()
            if self.self_gets==2:
                return {"success":True,"agent":{"name":"Different_Bob"}}
            return answer
        self.me=second_identity
        self.assertEqual(self.exercise(),"uncertain")
        self.assertEqual(self.posts,0)
        self.assertEqual(self.db.execute(
            "SELECT state FROM r4_action_outbox").fetchone(),("uncertain",))
        self.assertEqual(self.exercise(),"no_queued_r4_action")

    def test_original_publisher_adapter_full_fake_transport_and_once_only(self):
        calls=[]
        def api(method,path,payload=None,*,key=None):
            calls.append((method,path,key))
            self.assertEqual(key,"test-only-credential")
            if method=="GET":
                self.assertEqual(path,"/agents/me")
                return self.me()
            return self.post(method,path)
        with patch.object(common,"DATA",self.data):
            outcome=adapter._send_step(
                self.db,api_call=api,
                credential_loader=lambda:"test-only-credential",
                clock=self.clock,public_get=self.get_post,
                global_pause=lambda:self.paused)
            self.assertEqual(outcome,
                "R4 upvote: api_acknowledged_not_public_receipt")
            self.assertEqual(self.gets,2)
            self.assertEqual(self.self_gets,2)
            self.assertEqual(self.posts,1)
            again=adapter._send_step(
                self.db,api_call=api,
                credential_loader=lambda:self.fail("no credential after attempt"),
                clock=self.clock,public_get=lambda *_:self.fail("no remote replay"),
                global_pause=lambda:False)
        self.assertIsNone(again)
        self.assertEqual(calls[-1][:2],
                         ("POST","/posts/"+POST+"/upvote"))

    def test_original_publisher_public_hook_is_completely_compiled_off(self):
        self.assertTrue(adapter.R4_REAL_DISPATCH_COMPILED_OFF)
        self.assertTrue(adapter.R4_EXACT_OWNER_SEND_COMPILED_OFF)
        self.assertTrue(outbox.PUBLIC_DISPATCH_COMPILED_OFF)
        self.assertIsNone(adapter.maybe_r4_publisher_step(
            self.db,
            api_call=lambda *_:self.fail("public send gate bypass"),
            credential_loader=lambda:self.fail("creds gate bypass")))

    def test_adapter_refuses_when_signed_release_host_not_attested(self):
        with patch.object(adapter,"R4_REAL_DISPATCH_COMPILED_OFF",False), \
             patch.object(adapter,"R4_EXACT_OWNER_SEND_COMPILED_OFF",False), \
             patch.object(adapter,"_host_verified",return_value=False):
            result=adapter.maybe_r4_publisher_step(
                self.db,
                api_call=lambda *_:self.fail("unverified host must not request"),
                credential_loader=lambda:self.fail("unverified credential access"))
        self.assertEqual(result,"R4 refused: exact installed host/source gate")

    def test_adapter_malformed_api_ack_yields_uncertain_not_public_proof(self):
        def fake(method,path,payload=None,*,key=None):
            if method=="GET":
                return self.me()
            return {"ok":True}
        with patch.object(common,"DATA",self.data):
            result=adapter._send_step(
                self.db,api_call=fake,
                credential_loader=lambda:"test-only",
                clock=self.clock,public_get=self.get_post,
                global_pause=lambda:False)
        self.assertEqual(result,"R4 upvote: uncertain_no_replay")
        self.assertEqual(self.db.execute(
            "SELECT state FROM r4_action_outbox").fetchone(),("uncertain",))

    def test_file_backed_rehearsal_refuses_even_if_callbacks_fake(self):
        with tempfile.TemporaryDirectory() as t:
            db=sqlite3.connect(Path(t)/"never-send.sqlite3")
            self.addCleanup(db.close)
            with self.assertRaisesRegex(ValueError,"requires_memory_db"):
                lab.simulate_verified_attempt(
                    db,self.data,clock=self.clock,
                    post_get=self.get_post,self_get=self.me,
                    post_call=self.post,global_pause=lambda:False)


if __name__=="__main__":
    unittest.main()
