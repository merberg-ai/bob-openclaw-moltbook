"""R3.11 actual legacy publisher CLI against a private fake-transport fixture.

Never connects to Moltbook or reads the installed credential file. The only
accepted fixture carries a synthetic-only marker and private file permissions.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tests")]
from bob_v08.core import Action
from bob_v08.r311_inert_entry import (
    run_inert_entry, recover_inert_entry, SimulatedPowerLoss, DESCRIPTOR,
)
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_v08.r3_unified import UnifiedLab, _validated
from test_r3_cutover_rehearsal import make_saved_scout
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW

PUBLISHER=ROOT/"src"/"bin"/"bob-moltbook-publisher"


class PublisherEntrypointTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.source=self.root/"scout"
        make_saved_scout(self.source)
        self.action=Action("comment",RUN,ID,"Technical source discussion.",TEXT)
        obs,_=verified_source(self.source,self.action)
        self.path=self.root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.path)
        self.lab=UnifiedLab(self.path)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
        self.assertEqual(self.lab.propose(self.action,obs,at=NOW).state,"proposed")
        self.assertEqual(self.lab.queue(self.action,obs,mode="auto",
                                        at=NOW,policy=consent_policy()).state,
                         "queued_simulated")
        descriptor=self.root/DESCRIPTOR
        descriptor.write_text(json.dumps({
            "run_id":RUN, "post_id":ID, "reason":self.action.reason,
            "text":self.action.text}),encoding="utf-8")
        os.chmod(descriptor,0o600)

    def queue(self):
        with sqlite3.connect(self.path) as db:
            return db.execute(
                "SELECT state,attempted_at,comment_id FROM publish_jobs "
                "WHERE run_id=?", (RUN,)).fetchone()

    def event_count(self,kind):
        with sqlite3.connect(self.path) as db:
            return db.execute(
                "SELECT COUNT(*) FROM r3_lab_audit WHERE event=?", (kind,)
            ).fetchone()[0]

    def run_cli(self,mode="--r311-inert-rehearsal",path=None):
        env=os.environ.copy()
        env["PYTHONPATH"]=os.pathsep.join((str(ROOT/"src"),
                         str(ROOT/"src"/"lib"/"bob"), env.get("PYTHONPATH","")))
        env["HOME"]=str(self.root)
        return subprocess.run([sys.executable,str(PUBLISHER),mode,
                               str(path or self.path)],env=env,
                              capture_output=True,text=True,timeout=15,check=False)

    def test_real_publisher_executable_inert_cli_ack_without_network(self):
        result=self.run_cli()
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        report=json.loads(result.stdout)
        self.assertEqual(report["format"],"bob-r311-inert-entry-v1")
        self.assertEqual(report["state"],"acknowledged_simulated")
        self.assertTrue(report["attempt_recorded"])
        self.assertEqual(report["inert_sink_calls"],1)
        self.assertEqual(report["external_requests"],0)
        self.assertEqual(report["credential_reads"],0)
        self.assertEqual(report["installed_changes"],0)
        self.assertFalse(report["dispatch_authorized"])
        self.assertFalse(report["acted"])
        self.assertFalse(report["cutover_authorized"])
        self.assertNotIn(TEXT,result.stdout)
        self.assertNotIn(str(self.path),result.stdout)
        self.assertEqual(self.queue()[0],"acknowledged_simulated")
        self.assertIsNotNone(self.queue()[1])
        self.assertEqual(self.event_count("r310_claim"),1)
        self.assertEqual(self.event_count("r38_receipt"),1)

    def test_real_publisher_executable_second_run_never_replays(self):
        first=self.run_cli()
        self.assertEqual(first.returncode,0,first.stdout+first.stderr)
        second=self.run_cli()
        self.assertNotEqual(second.returncode,0)
        report=json.loads(second.stdout)
        self.assertEqual(report["state"],"refused")
        self.assertEqual(report["external_requests"],0)
        self.assertEqual(report["inert_sink_calls"],0)
        self.assertEqual(self.event_count("r310_claim"),1)
        self.assertEqual(self.event_count("r38_receipt"),1)

    def test_real_publisher_executable_refuses_old_live_queue_path(self):
        other=self.root/"activity-queue.sqlite3"
        response=self.run_cli(path=other)
        self.assertNotEqual(response.returncode,0)
        report=json.loads(response.stdout)
        self.assertEqual(report["reason"],"invalid_private_inert_fixture")
        self.assertFalse(other.exists())
        self.assertEqual(self.queue(),("queued",None,None))

    def test_existing_publisher_main_path_has_no_r311_import_or_dispatch(self):
        source=PUBLISHER.read_text(encoding="utf-8")
        old=source[source.index("def publisher_step(db):"):
                   source.index("\ndef verification_step(db):")]
        self.assertNotIn("r311",old)
        self.assertNotIn("r310",old)
        self.assertIn("record=load_record(rid)",old)
        self.assertIn("api('POST',f'/posts/{pid}/comments'",old)
        footer=source[source.index("def r311_inert_cli(argv):"):]
        self.assertIn("raise SystemExit(main())",footer)
        self.assertIn("if len(sys.argv)>1 and sys.argv[1].startswith('--r311-')",footer)

    def test_missing_r3_settings_remain_off_despite_v07_auto_enabled(self):
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM publish_settings WHERE name IN "
                       "('r3_auto_enabled','r3_comment_dial')")
        result=self.run_cli()
        self.assertNotEqual(result.returncode,0)
        report=json.loads(result.stdout)
        self.assertEqual(report["reason"],"review_owner_r3_dial_off")
        self.assertEqual(self.queue(),("queued",None,None))
        self.assertEqual(self.event_count("r310_claim"),0)

    def test_revoked_owner_consent_blocks_the_actual_entrypoint(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_settings SET value='0' "
                       "WHERE name='r3_auto_enabled'")
        result=self.run_cli()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout)["reason"],
                         "review_separate_r3_auto_consent_required")
        self.assertIsNone(self.queue()[1])

    def test_changed_descriptor_draft_cannot_borrow_old_scout_approval(self):
        descriptor=self.root/DESCRIPTOR
        obj=json.loads(descriptor.read_text())
        obj["text"]="An entirely different new message from Bob."
        descriptor.write_text(json.dumps(obj))
        result=self.run_cli()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout)["reason"],
                         "invalid_private_inert_fixture")
        self.assertIsNone(self.queue()[1])

    def test_descriptor_symlink_or_public_permissions_rejected(self):
        original=self.root/DESCRIPTOR
        renamed=self.root/"private-original.json"
        original.rename(renamed)
        original.symlink_to(renamed)
        self.assertEqual(json.loads(self.run_cli().stdout)["reason"],
                         "invalid_private_inert_fixture")
        original.unlink()
        renamed.rename(original)
        os.chmod(original,0o644)
        self.assertEqual(json.loads(self.run_cli().stdout)["reason"],
                         "invalid_private_inert_fixture")
        self.assertEqual(self.queue(),("queued",None,None))

    def test_inert_fault_after_durable_intent_recovers_without_sending(self):
        with self.assertRaisesRegex(SimulatedPowerLoss,"after_synthetic_intent"):
            run_inert_entry(self.path,fault="after_intent")
        self.assertEqual(self.queue()[0],"sending_simulated")
        recovered=self.run_cli(mode="--r311-inert-recover")
        self.assertEqual(recovered.returncode,0)
        report=json.loads(recovered.stdout)
        self.assertEqual(report["state"],"recovered_simulated")
        self.assertEqual(report["inert_sink_calls"],0)
        self.assertFalse(report["dispatch_authorized"])
        self.assertEqual(self.queue()[0],"uncertain")
        self.assertIsNotNone(self.queue()[1])
        self.assertNotEqual(self.run_cli().returncode,0)

    def test_fault_after_inert_sink_never_resends_on_restart(self):
        with self.assertRaisesRegex(SimulatedPowerLoss,"after_inert_sink"):
            run_inert_entry(self.path,fault="after_sink")
        self.assertEqual(self.queue()[0],"sending_simulated")
        recovered=recover_inert_entry(self.path)
        self.assertEqual(recovered.state,"recovered_simulated")
        self.assertEqual(self.queue()[0],"uncertain")
        self.assertEqual(self.event_count("r310_claim"),1)
        self.assertEqual(self.event_count("r38_receipt"),0)
        self.assertEqual(self.run_cli().returncode,3)

    def test_fake_transport_timeout_is_unknown_and_locked(self):
        result=run_inert_entry(self.path,response="timeout")
        self.assertEqual(result.state,"uncertain_simulated")
        self.assertEqual(result.sink_calls,1)
        self.assertFalse(result.acted)
        self.assertEqual(self.queue()[0],"uncertain")
        self.assertNotEqual(self.run_cli().returncode,0)

    def test_fake_verification_challenge_needs_human_not_automatic(self):
        result=run_inert_entry(self.path,response="challenge")
        self.assertEqual(result.state,"awaiting_verification_simulated")
        self.assertEqual(self.queue()[0],"awaiting_verification_simulated")
        self.assertIsNotNone(self.queue()[1])
        self.assertFalse(result.dispatch_authorized)

    def test_private_fixture_competing_cli_processes_single_attempt(self):
        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes=list(workers.map(lambda _ :self.run_cli(),(0,1)))
        self.assertEqual(sum(x.returncode==0 for x in outcomes),1)
        self.assertEqual(self.event_count("r310_claim"),1)
        self.assertEqual(self.event_count("r38_receipt"),1)

    def test_legacy_uncertain_history_is_preserved_by_recovery(self):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO publish_jobs("
                       "run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,attempted_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("20261030T210000Z","a"*64,
                        "33333333-3333-4333-8333-333333333333",
                        "historical uncertain text","manual","uncertain",
                        NOW.isoformat(),NOW.isoformat(),NOW.isoformat()))
        result=recover_inert_entry(self.path)
        self.assertEqual(result.state,"recovered_simulated")
        with sqlite3.connect(self.path) as db:
            state=db.execute("SELECT state,attempted_at FROM publish_jobs "
                             "WHERE run_id='20261030T210000Z'").fetchone()
        self.assertEqual(state,("uncertain",NOW.isoformat()))

    def test_no_installer_or_real_credentials_referenced_in_rehearsal_module(self):
        import bob_v08.r311_inert_entry as m
        source=inspect.getsource(m)
        for forbidden in ("urllib", "HTTPSConnection", "api_key(",
                          "OPENER.open(", "systemctl", "subprocess.run(",
                          "moltbook.com"):
            self.assertNotIn(forbidden,source)
        self.assertFalse(run_inert_entry(self.path).dispatch_authorized)


if __name__=="__main__":
    unittest.main()
