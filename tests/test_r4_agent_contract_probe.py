"""Isolated R4 model/contract diagnostic tests: no real agent or social API."""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import patch
from io import StringIO
from pathlib import Path
import sys
import sqlite3
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_r4_agent_contract as probe


class R4LiveAgentContractSourceTests(unittest.TestCase):
    def test_known_transport_and_exact_parser_failures_can_be_identified(self):
        for label in (
            "shadow_agent_cli_failed","shadow_agent_payload_invalid",
            "r4_invalid_decision_json","r4_invalid_exact_eight_field_schema",
            "r4_changed_source_id","r4_invalid_skip_fields",
            "r4_model_changed_post_target",
            "r4_model_selected_disabled_action",
        ):
            with self.subTest(label=label):
                self.assertEqual(probe.safe_error(ValueError(label)),label)

    def test_never_echo_arbitrary_private_model_data(self):
        private="private token: plain text returned by Bob"
        self.assertEqual(probe.safe_error(RuntimeError(private)),
                         "unclassified_error")
        with redirect_stdout(StringIO()) as output:
            report=probe.result(stage=private,reason=private,called=True,
                                verified_kind=private)
            print(report)
        visible=output.getvalue()
        self.assertNotIn(private,visible)
        self.assertEqual(report["stage"],"host")
        self.assertEqual(report["reason"],"unclassified_error")
        self.assertEqual(report["verified_action_kind"],"none")

    def test_every_classified_result_denies_social_effects(self):
        for stage in ("host","source","controls","transport",
                      "contract","valid_private_decision"):
            report=probe.result(stage=stage,reason="ok")
            for flag in (
                "r4_decision_recorded","r4_proposal_queued",
                "public_social_dispatch_authorized",
                "publisher_or_service_changed_by_probe",
                "production_database_writes_by_probe"):
                self.assertIs(report[flag],False)

    def test_prior_source_owner_reports_exact_ledger_without_row_content(self):
        db=sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.executescript("""
          CREATE TABLE r4_social_decisions (source_run TEXT);
          CREATE TABLE r3_proposals (source_run TEXT);
          CREATE TABLE publish_jobs (run_id TEXT);
        """)
        old=probe.PREVIOUS_RUN
        self.assertEqual(probe._ledger_owner(db,old),"none")
        db.execute("INSERT INTO r3_proposals VALUES (?)",(old,))
        self.assertEqual(probe._ledger_owner(db,old),"r3")
        db.execute("INSERT INTO publish_jobs VALUES (?)",(old,))
        self.assertEqual(probe._ledger_owner(db,old),"multiple")

    def test_selector_skips_used_and_stale_follows_installed_order(self):
        when=datetime(2026,11,2,5,0,tzinfo=timezone.utc)
        old=SimpleNamespace(run_id=probe.PREVIOUS_RUN)
        available=SimpleNamespace(run_id="20261102T043700Z")
        stale=SimpleNamespace(run_id="20261025T043700Z")
        db=sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.executescript("""
          CREATE TABLE r4_social_decisions (source_run TEXT);
          CREATE TABLE r3_proposals (source_run TEXT);
          CREATE TABLE publish_jobs (run_id TEXT);
        """)
        db.execute("INSERT INTO r3_proposals VALUES (?)",(old.run_id,))
        self.assertIs(probe._next_available(
            db,[old,stale,available],when),available)
        db.execute("INSERT INTO r4_social_decisions VALUES (?)",
                   (available.run_id,))
        self.assertIsNone(probe._next_available(
            db,[old,stale,available],when))
        self.assertEqual(probe.result(stage="source",
                                     reason="no_fresh_r4_source",
                                     previous_owner="r3")["source_run"],"")

    def test_report_provenance_is_bounded_and_safe(self):
        report=probe.result(stage="contract",reason="r4_invalid_decision_json",
                            called=True,source_run="20261102T043700Z",
                            previous_owner="r3")
        self.assertEqual(report["source_run"],"20261102T043700Z")
        self.assertEqual(report["historical_source_run"],probe.PREVIOUS_RUN)
        self.assertEqual(report["historical_source_owner"],"r3")
        self.assertFalse(report["r4_proposal_queued"])
        self.assertFalse(report["public_social_dispatch_authorized"])

    def test_diagnostic_main_explicit_one_call_flag(self):
        output=StringIO()
        with redirect_stdout(output):
            self.assertEqual(probe.main(["--install"]),2)
        self.assertIn("one local OpenClaw",output.getvalue())

    def test_signed_modules_only_and_no_write_api(self):
        source=(ROOT/"scripts/report_r4_agent_contract.py").read_text()
        for needle in (
            'SESSION_PREFIX="moltbook-v08-shadow-r4-diagnostic-"',
            'from bob_r4_agent import decide,AVAILABLE',
            'from bob_v08.shadow import openclaw_decide',
            'from bob_v08.evidence import latest_observations',
            'from bob_r313d_package import load_verified',
            'import bob_r4_installed_gate as installed_gate',
            'if not installed_gate.verify():',
            'db.execute("PRAGMA query_only=ON")',
            'sqlite3.connect(DB.as_uri()+"?mode=ro"',
            'decision=decide(observed,modes=modes,model=model,now=now,',
            'reason=safe_error(exc)',
            'choices=latest_observations(DATA,max_scan=100,limit=20)',
            'observed=_next_available(db,choices,now)',
        ):
            self.assertIn(needle,source)
        for forbidden in (
            "subprocess.run(", "record(db", "set_mode(", "set_pause(",
            "db.commit(", "INSERT INTO", "UPDATE publish", "DELETE FROM",
            "api_key(", "requests.post(", "urllib.request", "publish_jobs(",
            "openclaw_decide(prompt,session)",
        ):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
