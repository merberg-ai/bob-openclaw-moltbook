"""R3.6 host-readiness and draft-origin review: private fixtures and no writes."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import inspect
import json
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"scripts"),str(ROOT/"src"),str(ROOT/"tests")]

from report_r36_host_readiness import queue_schema, review, compact
from report_r3_cutover_inventory import UNITS
from bob_v08.core import Action
from bob_v08.r36_admission_contract import classify_draft
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_v08.r3_unified import UnifiedLab
from test_r35_migration_recovery import create_legacy_fixture
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW
from test_r3_cutover_rehearsal import make_saved_scout


class HostContractTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.dbpath=self.root/"r35-inert-fixtures"/"r35-legacy-queue-lab.sqlite3"
        create_legacy_fixture(self.dbpath)

    def test_schema_report_reads_only_legacy_metadata_including_unknown_delivery(self):
        before=self.dbpath.read_bytes()
        data=queue_schema(self.dbpath)
        self.assertEqual(data["legacy_contract"],"match")
        self.assertEqual(data["status"],"ok")
        self.assertEqual(data["attempted_jobs"],1)
        self.assertEqual(data["uncertain_jobs"],1)
        self.assertEqual(data["rows"]["publish_jobs"],2)
        self.assertEqual(data["additive_tables_present"],[])
        self.assertEqual(self.dbpath.read_bytes(),before)
        self.assertNotIn("private ambiguous",json.dumps(data))
        self.assertNotIn("post_id",json.dumps(data))
        self.assertFalse((self.dbpath.parent/"r35-legacy-queue-lab.sqlite3-wal").exists())

    def test_missing_database_never_created_and_untrusted_symlink_refused(self):
        absent=self.root/"new.sqlite3"
        self.assertEqual(queue_schema(absent)["status"],"unavailable")
        self.assertFalse(absent.exists())
        alias=self.root/"alias.sqlite3"
        alias.symlink_to(self.dbpath)
        self.assertEqual(queue_schema(alias)["status"],"unavailable")

    def test_missing_required_column_blocks_compatibility(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute("ALTER TABLE decisions RENAME TO decisions_old")
            db.execute("CREATE TABLE decisions(run_id TEXT)")
        report=queue_schema(self.dbpath)
        self.assertEqual(report["legacy_contract"],"mismatch")
        self.assertIn("decisions",report["tables_missing"])

    def test_additive_schema_present_is_informational_and_never_authorizes(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute("CREATE TABLE r3_proposals(source_run TEXT)")
        report=queue_schema(self.dbpath)
        self.assertEqual(report["additive_tables_present"],["r3_proposals"])

    def fake_units(self, scope, name):
        expected = name != "bob-r3-candidate-publisher.service" and name != "bob-r3-candidate-publisher.timer"
        active = "active" if name in (
            "bob-moltbook-publisher.timer", "bob-v08-shadow.timer",
            "bob-startup-reconcile.timer") else "inactive"
        return dict(scope=scope,unit=name,load="loaded" if expected else "not-found",
                    active=active,sub="waiting" if active=="active" else "dead",
                    enabled="enabled" if active=="active" else "disabled",
                    result="success")

    def test_full_report_distinguishes_baseline_from_cutover_permission(self):
        data=review(queue_path=self.dbpath,
          paused_path=self.root/"paused",
          unit_reader=self.fake_units,
          queue_reader=lambda _p,paused:dict(status="ok",policy_status="valid",
                     pause="not_paused",auto_enabled="disabled",
                     policy_limits={"comment_daily":2},mode_counts={"manual/queued":1}),
          schema_reader=queue_schema)
        self.assertTrue(data["baseline_observed"])
        self.assertEqual(data["review_blockers"],[])
        self.assertFalse(data["cutover_authorized"])
        self.assertFalse(data["new_publisher_installed_by_report"])
        self.assertEqual(data["queue_contract"]["uncertain_jobs"],1)
        self.assertEqual(len(data["units"]),len(UNITS))
        self.assertEqual(data["queue_state"]["auto_enabled"],"disabled")
        self.assertIn("publisher",data["production_cutover_requirements"][0])
        short=compact(data)
        self.assertIn("cutover authorized: NO",short)
        self.assertIn("legacy queue schema: match",short)
        self.assertIn("delivery states requiring review: 1",short)
        self.assertNotIn("private ambiguous",short)

    def test_active_candidate_and_untrusted_unit_text_are_rejected_and_sanitized(self):
        def hostile(scope,name):
            row=self.fake_units(scope,name)
            if name == "bob-r3-candidate-publisher.timer":
                row["active"]="active"
            if name == "bob-moltbook-publisher.service":
                row["result"]="moltbook_TOKEN_SECRETVALUE"
                row["Environment"]="VERY_SECRET"
            return row
        data=review(queue_path=self.dbpath,
            paused_path=self.root/"paused", unit_reader=hostile,
            queue_reader=lambda _p,paused:dict(status="unavailable",
                       policy_status="unavailable",pause="unavailable"),
            schema_reader=queue_schema)
        self.assertFalse(data["baseline_observed"])
        self.assertIn("candidate_publisher_not_proven_inert",data["review_blockers"])
        self.assertIn("legacy_queue_policy_unverified",data["review_blockers"])
        self.assertIn("legacy_pause_state_unverified",data["review_blockers"])
        self.assertNotIn("VERY_SECRET",json.dumps(data))
        self.assertNotIn("SECRETVALUE",json.dumps(data))

    def test_invalid_system_scout_scope_does_not_fake_health(self):
        def unexpected(scope,name):
            row=self.fake_units(scope,name)
            if scope=="system" and name=="bob-moltbook-scout.timer":
                row["active"]="unknown"
            return row
        data=review(queue_path=self.dbpath,paused_path=self.root/"paused",
            unit_reader=unexpected,
            queue_reader=lambda _p,paused:dict(status="ok",policy_status="valid",
                        pause="not_paused"),schema_reader=queue_schema)
        self.assertIn("legacy_system_scout_not_confirmed_inactive",data["review_blockers"])


class DraftOriginTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"scout"
        self.record=make_saved_scout(self.source)
        self.dbpath=self.root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.dbpath)
        self.lab=UnifiedLab(self.dbpath)
        self.action=Action("comment",RUN,ID,"Source-based technical interest.",TEXT)
        self.obs,self.pin=verified_source(self.source,self.action)

    def read_classification(self, action=None):
        with sqlite3.connect(self.dbpath.absolute().as_uri()+"?mode=ro",
                             uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            return classify_draft(db,self.source,action or self.action)

    def test_new_bob_authored_comment_origin_requires_exact_r3_proposal(self):
        self.assertEqual(self.lab.propose(self.action,self.obs,at=NOW).state,"proposed")
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",
            at=NOW,policy=consent_policy()).state,"queued_simulated")
        before=self.dbpath.read_bytes()
        result=self.read_classification()
        self.assertEqual(result.origin,"r3_bob")
        self.assertEqual(result.reason,"origin_verified_requires_publisher_gate")
        self.assertTrue(result.source_verified)
        self.assertFalse(result.dispatch_authorized)
        self.assertEqual(self.dbpath.read_bytes(),before)
        changed=replace(self.action,text="Other words Bob never sealed.")
        self.assertEqual(self.read_classification(changed).origin,"refused")

    def test_legacy_scout_draft_is_separate_from_bob_comment(self):
        draft=self.record["draft_comment"]
        old=replace(self.action,text=draft)
        with sqlite3.connect(self.dbpath) as db:
            db.execute("""INSERT INTO publish_jobs (
                run_id,approval_sha256,post_id,draft_comment,mode,state,
                created_at,updated_at) VALUES(?,?,?,?,?,'queued',?,?)""",
                (RUN,self.record["approval_sha256"],ID,draft,"manual",
                 NOW.isoformat(),NOW.isoformat()))
        result=self.read_classification(old)
        self.assertEqual(result.origin,"legacy_scout")
        self.assertFalse(result.dispatch_authorized)
        self.assertEqual(self.read_classification().origin,"refused")

    def test_unsealed_forged_bob_text_not_reclassified_as_trusted(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute("""INSERT INTO publish_jobs (
                run_id,approval_sha256,post_id,draft_comment,mode,state,
                created_at,updated_at) VALUES(?,?,?,?,?,'queued',?,?)""",
                (RUN,"z"*64,ID,TEXT,"auto",NOW.isoformat(),NOW.isoformat()))
        result=self.read_classification()
        self.assertEqual((result.origin,result.reason),("refused","unrecognized_seal"))

    def test_later_source_corruption_invalidates_queue_review(self):
        self.lab.propose(self.action,self.obs,at=NOW)
        self.lab.queue(self.action,self.obs,mode="auto",
                       at=NOW,policy=consent_policy())
        (self.source/("scout-feed-"+RUN+".json")).write_text(
            '{"posts":[]}',encoding="utf-8")
        result=self.read_classification()
        self.assertEqual(result.reason,"saved_scout_source_unverified")

    def test_attempted_queue_cannot_pass_origin_review(self):
        self.lab.propose(self.action,self.obs,at=NOW)
        self.lab.queue(self.action,self.obs,mode="auto",
                       at=NOW,policy=consent_policy())
        with sqlite3.connect(self.dbpath) as db:
            db.execute("UPDATE publish_jobs SET state='uncertain',"
                       "attempted_at=? WHERE run_id=?",(NOW.isoformat(),RUN))
        self.assertEqual(self.read_classification().reason,
                         "job_changed_or_not_pending")

    def test_contract_module_has_no_network_or_publisher_dispatch(self):
        import bob_v08.r36_admission_contract as module
        source=inspect.getsource(module)
        for forbidden in ("urllib","requests.","api_key(","subprocess.run(",
                          "systemctl","moltbook.com"):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
