"""R3.13c source-only real-publisher-shaped R3 tests: NO network/credentials.

The candidate is invoked only with an existing marker-verified UnifiedLab
fixture, sealed action envelope, and fake GET/POST functions in-process.
The actual publisher entrypoint stays compiled Off even with owner flags On.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.machinery
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"src"/"lib"/"bob"),
                str(ROOT/"tests")]
from bob_v08.core import Action
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_v08.r3_unified import UnifiedLab, _validated
from bob_v08.r39_publisher_review import RemoteReview
from bob_v08.r313c_candidate import (
    ENVELOPE_DDL, canonical_action, candidate_step,
    recover_inflight, _read_envelope,
)
from bob_r313c_adapter import (
    R313C_REAL_DISPATCH, production_dispatch_enabled,
    maybe_r3_publisher_step,
)
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW
from test_r3_cutover_rehearsal import make_saved_scout

PUBLISHER = ROOT/"src"/"bin"/"bob-moltbook-publisher"
CID = "77777777-7777-4777-8777-777777777777"


def actual_publisher():
    loader = importlib.machinery.SourceFileLoader(
        "bob_publisher_r313c_isolated", str(PUBLISHER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    obj = importlib.util.module_from_spec(spec)
    loader.exec_module(obj)
    return obj


class R313COfflineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root/"scout"
        make_saved_scout(self.source)
        self.action = Action("comment", RUN, ID, "Technical explanation.", TEXT)
        self.obs, _ = verified_source(self.source, self.action)
        self.path = self.root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.path)
        self.lab = UnifiedLab(self.path)
        with closing(sqlite3.connect(self.path, isolation_level=None)) as db:
            db.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
            db.execute(ENVELOPE_DDL)
            db.execute("CREATE TABLE r313c_schema_meta("
                       "name TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO r313c_schema_meta VALUES"
                       "('version','r313c-action-v1')")
            db.execute("INSERT INTO publish_settings VALUES"
                       "('r3_manual_enabled','0')")
        self.assertEqual(
            self.lab.propose(self.action,self.obs,at=NOW).state,"proposed")
        self.assertEqual(self.lab.queue(
            self.action,self.obs,mode="auto",at=NOW,
            policy=consent_policy()).state,"queued_simulated")
        self.seed_envelope()

    def seed_envelope(self):
        action_json = canonical_action(self.action)
        seal, _ = _validated(self.action, self.obs)
        with closing(sqlite3.connect(self.path, isolation_level=None)) as db:
            db.execute("INSERT OR REPLACE INTO r313c_action_envelopes "
                       "(source_run,action_json,action_sha256,seal_sha256,created_at)"
                       " VALUES(?,?,?,?,?)",
                       (RUN,action_json,hashlib.sha256(action_json.encode()).hexdigest(),
                        seal,NOW.isoformat()))

    def connect(self):
        return sqlite3.connect(self.path,timeout=8,isolation_level=None)

    def exercise(self, *, response="ack", db=None, after_intent=None, after_post=None,
            post=None, remote=None):
        calls=[]
        def fake_post(target,text):
            self.assertEqual(target,ID)
            self.assertEqual(text,TEXT)
            calls.append(hashlib.sha256(text.encode()).hexdigest())
            if post is not None:
                return post(target,text)
            if response=="timeout":
                raise TimeoutError("no external network")
            if response=="challenge":
                return {"success":True,"verification_required":True,
                        "verification":{"verification_code":"moltbook_fake",
                                        "challenge_text":"Solve manually",
                                        "expires_at":"2026-10-30T23:40:00Z"}}
            if response=="malformed":
                return {"success":True}
            if response=="rejected":
                return {"success":False}
            return {"success":True,"comment":{"id":CID}}
        def fake_get(post,author):
            if remote is not None:
                return remote(post,author)
            return RemoteReview(post==ID and author==self.obs.author,
                                "fake_exact_identity")
        if db is not None:
            return candidate_step(db,self.source,self.root/"paused",
                      clock=lambda:NOW,public_get=fake_get,
                      post_comment=fake_post,
                      after_intent=after_intent, after_post=after_post),calls
        with closing(self.connect()) as con:
            return candidate_step(con,self.source,self.root/"paused",
                      clock=lambda:NOW,public_get=fake_get,
                      post_comment=fake_post,
                      after_intent=after_intent,after_post=after_post),calls

    def row(self):
        with closing(self.connect()) as db:
            return db.execute("SELECT state,attempted_at,comment_id "
                              "FROM publish_jobs WHERE run_id=?", (RUN,)).fetchone()

    def test_actual_publisher_still_hard_off_and_does_not_load_key(self):
        p=actual_publisher()
        p.auto_candidates=lambda db: 0
        p.checkpoint=lambda *a,**k:None
        p.api=lambda *a,**k: (_ for _ in ()).throw(
            AssertionError("network must stay Off"))
        p.api_key=lambda: (_ for _ in ()).throw(
            AssertionError("credentials must stay Off"))
        self.assertFalse(R313C_REAL_DISPATCH)
        self.assertFalse(production_dispatch_enabled())
        with closing(self.connect()) as db:
            self.assertIsNone(maybe_r3_publisher_step(
                db,api_call=p.api,credential_loader=p.api_key))
            status=p.publisher_step(db)
        self.assertIn("held",status)
        self.assertEqual(self.row(),("queued",None,None))

    def test_canonical_envelope_checked_against_saved_scout_proposal(self):
        with closing(self.connect()) as db:
            self.assertEqual(_read_envelope(db,RUN),self.action)
            row=db.execute("SELECT action_json FROM r313c_action_envelopes").fetchone()
            self.assertEqual(row[0],canonical_action(self.action))
        result,calls=self.exercise()
        self.assertEqual(result.status,"api_acknowledged")
        self.assertTrue(result.attempted)
        self.assertEqual(len(calls),1)
        self.assertFalse(result.dispatch_authorized)
        self.assertEqual(result.external_requests,0)
        self.assertEqual(self.row()[0],"published")
        self.assertEqual(self.row()[2],CID)
        with closing(self.connect()) as db:
            audit=db.execute("SELECT reason FROM r3_lab_audit "
                             "WHERE event='r313c_receipt'").fetchone()
        self.assertEqual(audit[0],"api_ack_comment_id_not_publicly_reverified")

    def test_missing_or_tampered_reason_envelope_prevents_attempt(self):
        with closing(self.connect()) as db:
            db.execute("DELETE FROM r313c_action_envelopes")
        result,calls=self.exercise()
        self.assertEqual(result.status,"held")
        self.assertEqual(calls,[])
        self.assertIsNone(self.row()[1])
        self.seed_envelope()
        with closing(self.connect()) as db:
            obj=json.loads(canonical_action(self.action))
            obj["reason"]="A fabricated new motive."
            fake=json.dumps(obj,ensure_ascii=True,sort_keys=True,
                            separators=(",",":"))
            db.execute("UPDATE r313c_action_envelopes SET "
                       "action_json=?,action_sha256=?",
                       (fake,hashlib.sha256(fake.encode()).hexdigest()))
        result,calls=self.exercise()
        self.assertEqual(result.status,"held")
        self.assertEqual(calls,[])
        self.assertIsNone(self.row()[1])

    def test_revocation_of_auto_permission_before_claim(self):
        with closing(self.connect()) as db:
            db.execute("UPDATE publish_settings SET value='0' "
                       "WHERE name='r3_auto_enabled'")
        result,calls=self.exercise()
        self.assertEqual(result.status,"held")
        self.assertEqual(calls,[])
        self.assertIsNone(self.row()[1])

    def test_remote_identity_mismatch_blocks_without_attempt(self):
        result,calls=self.exercise(remote=lambda p,a:RemoteReview(False,"wrong_author"))
        self.assertEqual(result.status,"held")
        self.assertIn("wrong_author",result.reason)
        self.assertEqual(calls,[])
        self.assertIsNone(self.row()[1])

    def test_manual_independent_enable_exact_seal_required(self):
        with closing(self.connect()) as db:
            db.execute("UPDATE publish_jobs SET mode='manual' WHERE run_id=?",
                       (RUN,))
            db.execute("UPDATE publish_settings SET value='propose' "
                       "WHERE name='r3_comment_dial'")
            seal,_=_validated(self.action,self.obs)
            db.execute("INSERT INTO r3_owner_approvals VALUES(?,?,?,?)",
                       (RUN,seal,"approved",NOW.isoformat()))
        result,calls=self.exercise()
        self.assertEqual(result.status,"held")
        self.assertEqual(calls,[])
        with closing(self.connect()) as db:
            db.execute("UPDATE publish_settings SET value='1' "
                       "WHERE name='r3_manual_enabled'")
        result,calls=self.exercise()
        self.assertEqual(result.status,"api_acknowledged")
        self.assertEqual(len(calls),1)

    def test_pause_after_committed_intent_consumes_attempt_no_post(self):
        def pause():
            (self.root/"paused").touch(mode=0o600)
        result,calls=self.exercise(after_intent=pause)
        self.assertEqual(result.status,"uncertain")
        self.assertTrue(result.attempted)
        self.assertEqual(calls,[])
        self.assertIsNotNone(self.row()[1])
        again,newcalls=self.exercise()
        self.assertEqual(newcalls,[])
        self.assertEqual(again.status,"not_selected")

    def test_owner_revoke_after_intent_consumes_attempt_no_post(self):
        def revoke():
            with closing(self.connect()) as db:
                db.execute("UPDATE publish_settings SET value='off' "
                           "WHERE name='r3_comment_dial'")
        result,calls=self.exercise(after_intent=revoke)
        self.assertEqual((result.status,calls),("uncertain",[]))
        self.assertIn("owner",result.reason)
        self.assertIsNotNone(self.row()[1])

    def test_friend_added_after_intent_blocks_automatic_post(self):
        def added_friend():
            with closing(self.connect()) as db:
                db.execute("INSERT INTO bob_friends VALUES('savedagent')")
        result,calls=self.exercise(after_intent=added_friend)
        self.assertEqual(result.status,"uncertain")
        self.assertEqual(calls,[])
        self.assertIsNotNone(self.row()[1])

    def test_rejected_malformed_and_timeout_never_retry(self):
        for outcome in ("timeout","malformed","rejected"):
            with self.subTest(outcome=outcome):
                # Reset fixture state only for synthetic tests.
                with closing(self.connect()) as db:
                    db.execute("UPDATE publish_jobs SET state='queued',"
                               "attempted_at=NULL,comment_id=NULL")
                    db.execute("UPDATE r3_proposals SET state='queued'")
                result,calls=self.exercise(response=outcome)
                self.assertEqual(result.status,"uncertain")
                self.assertTrue(result.attempted)
                self.assertEqual(len(calls),1)
                again,calls2=self.exercise(response="ack")
                self.assertEqual(again.status,"not_selected")
                self.assertEqual(calls2,[])

    def test_challenge_requires_human_existing_publisher_verifier(self):
        result,calls=self.exercise(response="challenge")
        self.assertEqual(result.status,"awaiting_verification")
        self.assertEqual(len(calls),1)
        with closing(self.connect()) as db:
            self.assertEqual(db.execute(
                "SELECT state,challenge_code FROM publish_jobs WHERE run_id=?",
                (RUN,)).fetchone(),
                ("awaiting_verification","moltbook_fake"))
        self.assertEqual(self.exercise()[0].status,"not_selected")

    def test_crash_after_post_recovery_locks_attempt_not_replay(self):
        def crash():
            raise RuntimeError("synthetic process crash after fake post")
        with self.assertRaisesRegex(RuntimeError,"synthetic process crash"):
            self.exercise(after_post=crash)
        self.assertEqual(self.row()[0],"sending")
        with closing(self.connect()) as db:
            self.assertEqual(recover_inflight(db),1)
            self.assertEqual(recover_inflight(db),0)
        self.assertEqual(self.row()[0],"uncertain")
        result,calls=self.exercise()
        self.assertEqual(result.status,"not_selected")
        self.assertEqual(calls,[])

    def test_manual_priority_legacy_head_first(self):
        with closing(self.connect()) as db:
            db.execute("INSERT INTO publish_jobs (run_id,approval_sha256,"
                       "post_id,draft_comment,mode,state,created_at,updated_at)"
                       "VALUES(?,?,?,?,'manual','queued',?,?)",
                       ("20261030T225900Z", "f"*64,
                        "11111111-1111-4111-8111-111111111111",
                        "Legacy manual draft",NOW.isoformat(),NOW.isoformat()))
        result,calls=self.exercise()
        self.assertEqual(result.status,"not_selected")
        self.assertEqual(calls,[])
        self.assertIsNone(self.row()[1])

    def test_duplicate_prior_attempt_target_blocks(self):
        with closing(self.connect()) as db:
            db.execute("INSERT INTO publish_jobs (run_id,approval_sha256,"
                       "post_id,draft_comment,mode,state,created_at,"
                       "attempted_at,updated_at)"
                       "VALUES(?,?,?,?,'manual','failed',?,?,?)",
                       ("20261030T220000Z","f"*64,ID,
                        "Previously attempted",NOW.isoformat(),
                        NOW.isoformat(),NOW.isoformat()))
        result,calls=self.exercise()
        self.assertEqual(result.status,"held")
        self.assertEqual(calls,[])
        self.assertIsNone(self.row()[1])

    def test_concurrent_claim_only_one_fake_post(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers=list(pool.map(lambda _:self.exercise(),range(2)))
        posted=sum(len(calls) for _,calls in answers)
        self.assertEqual(posted,1)
        self.assertEqual(self.row()[0],"published")
        with closing(self.connect()) as db:
            count=db.execute(
                "SELECT COUNT(*) FROM r3_lab_audit WHERE event='r313c_claim'").fetchone()[0]
        self.assertEqual(count,1)

    def test_no_real_post_in_candidate_and_source_gate_hard_off(self):
        import bob_r313c_adapter as bridge
        code=inspect.getsource(bridge)
        self.assertIn("R313C_REAL_DISPATCH = False",code)
        self.assertIn("R312_REAL_DISPATCH",code)
        self.assertFalse(production_dispatch_enabled())
        self.assertNotIn("os.getenv",code)
        self.assertNotIn("os.environ",code)
        self.assertNotIn("urllib.request",code)
        self.assertEqual(self.row()[0],"queued")


if __name__=="__main__":
    unittest.main()
