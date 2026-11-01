"""One coherent R3 proposal -> owner -> SAME publisher rehearsal, offline.

This exercises production-shaped proposal and owner entrypoints plus the
single legacy publisher ADAPTER with mock transport and a fake installed
signed-package verifier. Production dispatch remains compiled Off in source.
No installed credentials, no real Moltbook requests and no systemd changes.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src/lib/bob"),str(ROOT/"tests"),
              str(ROOT/"scripts")]
import bob_r313c_adapter as adapter
import bob_r313d_package
from bob_v08.core import Action
from bob_v08.r313b_upgrade_contract import OFF_SETTINGS
from bob_v08.r313c_candidate import ENVELOPE_DDL,recover_inflight
from bob_v08.r313d_producer import propose_verified
from bob_v08.r39_publisher_review import RemoteReview
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_v08.r3_unified import UnifiedLab
from bob_r313d_owner import (
    control_state, decide_exact, set_owner_mode)
from test_r3_unified import fixture,RUN,ID,TEXT,NOW
from test_r3_cutover_rehearsal import make_saved_scout

RECEIPT="77777777-7777-4777-8777-777777777777"


class RealShapeE2E(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="bob-r3-full-chain-synthetic-")
        self.addCleanup(t.cleanup)
        self.home=Path(t.name)
        (self.home/".config/bob-system").mkdir(mode=0o700,parents=True)
        self.source=self.home/"scout"
        make_saved_scout(self.source)
        self.action=Action(
            "comment",RUN,ID,"Grounded synthetic owner decision.",TEXT)
        self.obs,_=verified_source(self.source,self.action)
        self.dbfile=self.home/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.dbfile)
        with closing(self.db()) as db:
            db.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
            db.execute("CREATE TABLE publish_events("
                       "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                       "at TEXT NOT NULL,kind TEXT NOT NULL,details TEXT NOT NULL)")
            db.execute(ENVELOPE_DDL)
            db.execute("CREATE TABLE r313c_schema_meta("
                       "name TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO r313c_schema_meta VALUES"
                       "('version','r313c-action-v1')")
            for key,value in OFF_SETTINGS.items():
                db.execute("INSERT OR REPLACE INTO publish_settings VALUES(?,?)",
                           (key,value))
        self.seal=hashlib.sha256(
            (ID+"\n"+TEXT+"\n"+self.obs.snapshot_sha256).encode()
        ).hexdigest()
        self.calls=[]
        self.keys=0

    def db(self):
        return sqlite3.connect(self.dbfile,isolation_level=None,timeout=6)

    def stage(self):
        with closing(self.db()) as db:
            created=propose_verified(db,self.source,self.action,at=NOW)
            self.assertEqual(created.status,"proposed")
            self.assertFalse(created.queued)
            self.assertFalse(created.attempted)
            self.assertFalse(created.dispatch_authorized)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)
            set_owner_mode(db,"manual-on","ENABLE R3 MANUAL")
            decide_exact(db,self.source,RUN,self.seal,"approve",clock=lambda:NOW)
            decide_exact(db,self.source,RUN,self.seal,"queue",clock=lambda:NOW)
            self.assertEqual(db.execute(
                "SELECT state,mode,attempted_at FROM publish_jobs WHERE run_id=?",
                (RUN,)).fetchone(),("queued","manual",None))
            self.assertFalse(control_state(db)["automatic"])

    def callback(self,method,path,payload=None,*,key=None):
        self.calls.append((method,path))
        if method!="POST" or path!="/posts/"+ID+"/comments":
            self.fail("adapter attempted an unexpected network operation")
        self.assertEqual(payload,{"content":TEXT})
        self.assertEqual(key,"synthetic-key-only")
        return {"success":True,"comment":{"id":RECEIPT}}

    def credential(self):
        self.keys+=1
        return "synthetic-key-only"

    def invoke(self, *, api=None, trusted=True, archive=True):
        def get(post,author):
            self.assertEqual(post,ID)
            self.assertEqual(author,self.obs.author)
            return RemoteReview(True,"synthetic_exact_author")
        with patch.object(adapter,"production_dispatch_enabled",return_value=True), \
             patch.object(adapter,"_trusted_single_publisher_db",
                          return_value=trusted), \
             patch.object(adapter,"DATA",self.source), \
             patch.object(bob_r313d_package,"load_verified",
                 return_value="verified_registry_archive" if archive else
                 "invalid_registry"), \
             patch("bob_v08.r39_publisher_review.public_get_post",side_effect=get), \
             patch.object(adapter.Path,"home",return_value=self.home), \
             closing(self.db()) as db:
            return adapter.maybe_r3_publisher_step(
                db,api_call=self.callback if api is None else api,
                credential_loader=self.credential)

    def queued_row(self):
        with closing(self.db()) as db:
            return db.execute(
                "SELECT state,attempted_at,comment_id FROM publish_jobs "
                "WHERE run_id=?",(RUN,)).fetchone()

    def test_exact_manual_chain_uses_one_signed_writer_and_one_transport(self):
        self.stage()
        outcome=self.invoke()
        self.assertEqual(outcome,"R3 candidate outcome: api_acknowledged")
        self.assertEqual(self.calls,[("POST","/posts/"+ID+"/comments")])
        self.assertEqual(self.keys,1)
        row=self.queued_row()
        self.assertEqual(row[0],"published")
        self.assertIsNotNone(row[1])
        self.assertEqual(row[2],RECEIPT)
        self.assertIsNone(self.invoke())
        self.assertEqual(len(self.calls),1)
        with closing(self.db()) as db:
            audit=db.execute("SELECT event,reason FROM r3_lab_audit "
                             "WHERE event='r313c_receipt'").fetchone()
        self.assertEqual(audit[1],
                         "api_ack_comment_id_not_publicly_reverified")
        self.assertFalse(adapter.production_dispatch_enabled())

    def test_owner_revocation_cancels_only_unattempted_bob_queue(self):
        self.stage()
        with closing(self.db()) as db:
            set_owner_mode(db,"all-off","DISABLE R3")
        self.assertEqual(self.queued_row(),("cancelled",None,None))
        self.assertIsNone(self.invoke())
        self.assertEqual(self.calls,[])
        self.assertEqual(self.keys,0)

    def test_untrusted_package_or_owner_prevents_credential_lookup(self):
        self.stage()
        self.assertEqual(self.invoke(archive=False),
                         "R3 installed archive unverified; no send")
        self.assertEqual(self.invoke(trusted=False),
                         "R3 candidate host boundary refused; no send")
        self.assertEqual(self.queued_row(),("queued",None,None))
        self.assertEqual(self.calls,[])
        self.assertEqual(self.keys,0)

    def test_timeout_leaves_durable_uncertain_without_second_attempt(self):
        self.stage()
        def timedout(*args,**kwargs):
            self.calls.append(("POST","timeout"))
            raise TimeoutError("synthetic only")
        self.assertEqual(self.invoke(api=timedout),
                         "R3 candidate outcome: uncertain")
        self.assertEqual(self.queued_row()[0],"uncertain")
        self.assertEqual(self.queued_row()[2],None)
        self.assertIsNone(self.invoke())
        self.assertEqual(self.calls,[("POST","timeout")])
        self.assertEqual(self.keys,1)

    def test_legacy_human_manual_job_has_priority_without_R3_claim(self):
        self.stage()
        with closing(self.db()) as db:
            db.execute(
                "INSERT INTO publish_jobs"
                "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                "created_at,updated_at) VALUES(?,?,?,?,'manual','queued',?,?)",
                ("20261030T203000Z","f"*64,
                 "11111111-1111-4111-8111-111111111111",
                 "synthetic legacy manual",NOW.isoformat(),NOW.isoformat()))
        self.assertIsNone(self.invoke())
        self.assertEqual(self.queued_row(),("queued",None,None))
        self.assertEqual(self.calls,[])
        self.assertEqual(self.keys,0)

if __name__=="__main__":
    unittest.main()
