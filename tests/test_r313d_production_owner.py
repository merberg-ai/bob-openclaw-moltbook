"""R3.13d Off-first production Controls and real-Bob proposal contract tests.

All fixtures are synthetic local SQLite files. The actual manager/publisher
and Moltbook credentials/services are not accessed. No external HTTP.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime,timezone
import hashlib
import inspect
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src"/"lib"/"bob"),
             str(ROOT/"tests"),str(ROOT/"scripts")]
from bob_v08.core import Action
from bob_v08.r313c_candidate import ENVELOPE_DDL, _read_envelope
from bob_v08.r313d_producer import propose_verified, ProposalResult
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_r313d_owner import (
    schema_ready,control_state,set_owner_mode,decide_exact,
    recent_proposals,R3_AUTO_UI_COMPILED_OFF,trusted_manager_boundary,
)
from test_r3_unified import fixture,RUN,ID,TEXT,NOW
from test_r3_cutover_rehearsal import make_saved_scout
from bob_v08.r313b_upgrade_contract import OFF_SETTINGS

class R313DOwnerTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.source=self.root/"scout"
        make_saved_scout(self.source)
        self.action=Action("comment",RUN,ID,
                           "Independent source-grounded observation.",TEXT)
        self.dbfile=self.root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.dbfile)
        with closing(self.connect()) as db:
            db.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
            db.execute("CREATE TABLE publish_events("
                       "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                       "at TEXT NOT NULL,kind TEXT NOT NULL,"
                       "details TEXT NOT NULL)")
            db.execute(ENVELOPE_DDL)
            db.execute("CREATE TABLE r313c_schema_meta "
                       "(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO r313c_schema_meta VALUES"
                       "('version','r313c-action-v1')")
            for key,value in OFF_SETTINGS.items():
                db.execute("INSERT OR REPLACE INTO publish_settings VALUES(?,?)",(key,value))
        self.seal=hashlib.sha256(
            (ID+"\n"+TEXT+"\n"+verified_source(self.source,self.action)[0].snapshot_sha256
             ).encode("utf-8")).hexdigest()

    def connect(self):
        return sqlite3.connect(self.dbfile,isolation_level=None,timeout=6)

    def propose(self):
        with closing(self.connect()) as db:
            return propose_verified(db,self.source,self.action,at=NOW)

    def test_schema_defaults_off_and_no_legacy_flag_inheritance(self):
        with closing(self.connect()) as db:
            self.assertTrue(schema_ready(db))
            self.assertFalse(control_state(db)["manual"])
            self.assertFalse(control_state(db)["automatic"])
            self.assertTrue(R3_AUTO_UI_COMPILED_OFF)
            self.assertFalse(trusted_manager_boundary(db))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM publish_jobs"
                                       ).fetchone()[0],0)
            with self.assertRaisesRegex(ValueError,"r3_automatic_publication_compiled_off"):
                set_owner_mode(db,"auto-on","ENABLE R3 AUTO")

    def test_verified_bob_action_created_as_proposal_only(self):
        result=self.propose()
        self.assertEqual(result.status,"proposed")
        self.assertFalse(result.queued)
        self.assertFalse(result.attempted)
        self.assertFalse(result.dispatch_authorized)
        with closing(self.connect()) as db:
            self.assertEqual(_read_envelope(db,RUN),self.action)
            self.assertEqual(db.execute(
                "SELECT state FROM r3_proposals WHERE source_run=?",
                (RUN,)).fetchone(),("proposed",))
            self.assertIsNone(db.execute("SELECT run_id FROM publish_jobs "
                        "WHERE run_id=?",(RUN,)).fetchone())
            self.assertEqual(recent_proposals(db,self.source)[0]["reason"],
                             self.action.reason)

    def test_owner_manual_requires_typed_confirmation_and_exact_seal(self):
        self.propose()
        with closing(self.connect()) as db:
            with self.assertRaisesRegex(ValueError,"owner_confirmation_mismatch"):
                set_owner_mode(db,"manual-on","ENABLE AUTO")
            with self.assertRaisesRegex(ValueError,"separate_r3_manual_owner_switch_off"):
                decide_exact(db,self.source,RUN,self.seal,"approve",clock=lambda:NOW)
            set_owner_mode(db,"manual-on","ENABLE R3 MANUAL")
            self.assertTrue(control_state(db)["manual"])
            self.assertFalse(control_state(db)["automatic"])
            with self.assertRaisesRegex(ValueError,"bob_draft_seal_changed"):
                decide_exact(db,self.source,RUN,"f"*64,"approve",clock=lambda:NOW)
            decide_exact(db,self.source,RUN,self.seal,"approve",clock=lambda:NOW)
            self.assertEqual(recent_proposals(db,self.source)[0]["approval"],"approved")
            with self.assertRaisesRegex(ValueError,"r3_owner_decision_already_recorded"):
                decide_exact(db,self.source,RUN,self.seal,"approve",clock=lambda:NOW)
            decide_exact(db,self.source,RUN,self.seal,"queue",clock=lambda:NOW)
            queued=db.execute("SELECT state,mode,attempted_at "
                              "FROM publish_jobs WHERE run_id=?",(RUN,)).fetchone()
            self.assertEqual(queued,("queued","manual",None))
            self.assertEqual(db.execute(
                "SELECT state FROM r3_proposals WHERE source_run=?",
                (RUN,)).fetchone(),("queued",))

    def test_revoke_cancels_unattempted_r3_only_preserves_legacy_and_history(self):
        self.propose()
        with closing(self.connect()) as db:
            set_owner_mode(db,"manual-on","ENABLE R3 MANUAL")
            decide_exact(db,self.source,RUN,self.seal,"approve",clock=lambda:NOW)
            decide_exact(db,self.source,RUN,self.seal,"queue",clock=lambda:NOW)
            db.execute("INSERT INTO publish_jobs "
                       "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,updated_at) VALUES(?,?,?,?,'manual','queued',?,?)",
                       ("20261030T225959Z","a"*64,
                        "22222222-2222-4222-8222-222222222222",
                        "LEGACY SCOUT MUST REMAIN",NOW.isoformat(),NOW.isoformat()))
            db.execute("INSERT INTO publish_jobs "
                       "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,attempted_at,updated_at)"
                       "VALUES(?,?,?,?,'manual','uncertain',?,?,?)",
                       ("20261030T210000Z","b"*64,
                        "33333333-3333-4333-8333-333333333333",
                        "HISTORICAL ATTEMPT",NOW.isoformat(),NOW.isoformat(),NOW.isoformat()))
            set_owner_mode(db,"all-off","DISABLE R3")
            self.assertEqual(db.execute("SELECT state FROM publish_jobs "
                             "WHERE run_id=?",(RUN,)).fetchone(),("cancelled",))
            self.assertEqual(db.execute("SELECT state FROM publish_jobs "
                             "WHERE run_id='20261030T225959Z'").fetchone(),("queued",))
            self.assertEqual(db.execute("SELECT state FROM publish_jobs "
                             "WHERE run_id='20261030T210000Z'").fetchone(),("uncertain",))
            self.assertFalse(control_state(db)["manual"])

    def test_reject_does_not_queue_and_requires_independent_seal(self):
        self.propose()
        with closing(self.connect()) as db:
            decide_exact(db,self.source,RUN,self.seal,"reject",clock=lambda:NOW)
            self.assertEqual(db.execute("SELECT state FROM r3_proposals"
                             ).fetchone(),("rejected",))
            self.assertIsNone(db.execute("SELECT run_id FROM publish_jobs").fetchone())

    def test_tampered_source_and_envelope_never_queue(self):
        self.propose()
        with closing(self.connect()) as db:
            set_owner_mode(db,"manual-on","ENABLE R3 MANUAL")
            db.execute("UPDATE r313c_action_envelopes "
                       "SET action_sha256='0' WHERE source_run=?",(RUN,))
            with self.assertRaises(ValueError):
                decide_exact(db,self.source,RUN,self.seal,"approve",clock=lambda:NOW)
            self.assertIsNone(db.execute(
                "SELECT source_run FROM r3_owner_approvals").fetchone())

    def test_old_legacy_target_blocks_bob_proposal(self):
        with closing(self.connect()) as db:
            db.execute("INSERT INTO publish_jobs (run_id,approval_sha256,"
                       "post_id,draft_comment,mode,state,created_at,updated_at)"
                       "VALUES(?,?,?,?,'auto','uncertain',?,?)",
                       ("20261030T210000Z","f"*64,ID,"legacy could have posted",
                        NOW.isoformat(),NOW.isoformat()))
            result=propose_verified(db,self.source,self.action,at=NOW)
            self.assertEqual(result.status,"refused")
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM r3_proposals").fetchone()[0],0)

    def test_uninstalled_package_loader_is_never_a_public_post_token(self):
        import bob_r313d_package
        import bob_v08.r313d_producer as producer
        self.assertFalse(producer.ProposalResult("proposed","test").dispatch_authorized)
        self.assertIn("verified_registry_archive",
                      inspect.getsource(bob_r313d_package.load_verified))
        self.assertNotIn("api_key(",inspect.getsource(producer))
        self.assertNotIn("http.client",inspect.getsource(producer))

class R313DBundleTests(unittest.TestCase):
    def test_generated_oc4_shadow_manager_keeps_original_source_pinned(self):
        import build_r313d_manager_candidate as generated
        import build_v071_manager_candidate as baseline
        old=baseline.SOURCE.read_bytes()
        self.assertEqual(baseline.sha256(old),
                         baseline.PINNED_BASELINE_SHA256)
        manager,nav=generated.build()
        self.assertIn(b"class Handler(R3HandlerMixin, _LegacyHandler):",manager)
        self.assertIn(b"R3_CSRF_TOKEN = TOKEN",manager)
        self.assertIn(b"bob_v08_bridge",manager)
        self.assertIn(b"/investigate",manager)
        self.assertIn(b"/r3",nav)
        self.assertIn(b"/v08/now",nav)
        self.assertIn(b"/v08/inbox",nav)
        self.assertEqual(old,baseline.SOURCE.read_bytes())

    def test_deterministic_build_is_separate_from_shadow4(self):
        import build_r313d_off_package
        a=build_r313d_off_package.build()
        b=build_r313d_off_package.build()
        self.assertEqual(a,b)
        self.assertLess(len(a[0]),512*1024)
        self.assertIn(b"bob-r3-propose",a[1])
        import zipfile
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(a[0])) as pkg:
            self.assertIn("bob_v08/r313d_producer.py",pkg.namelist())
            self.assertIn("bob_v08/r313c_candidate.py",pkg.namelist())

if __name__=="__main__":
    unittest.main()
