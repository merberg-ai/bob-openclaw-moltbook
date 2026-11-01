"""Read-only exact R3 public receipt, synthetic SQLite + fake GET only."""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]
import report_r3_canary_receipt as receipt

CID="11111111-2222-4333-8444-555555555555"
STAMP="2026-11-02T10:00:00+00:00"


class CanaryReceiptTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r3canary-receipt-")
        self.addCleanup(temp.cleanup)
        self.db=Path(temp.name)/"private.sqlite3"
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE publish_jobs(run_id TEXT,post_id TEXT,"
                         "mode TEXT,state TEXT,attempted_at TEXT,comment_id TEXT)")

    def one(self, *, run=receipt.RUN,post=receipt.POST,mode="manual",
            state="published",attempted=STAMP,comment=CID):
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO publish_jobs VALUES(?,?,?,?,?,?)",
                         (run,post,mode,state,attempted,comment))

    def test_unqueued_has_no_public_send_or_receipt(self):
        data=receipt.report(_synthetic_db=self.db)
        self.assertEqual(data["state"],"not_queued")
        self.assertFalse(data["attempt_recorded"])
        self.assertFalse(data["independently_visible"])
        self.assertFalse(data["retry_authorized"])

    def test_api_ack_not_public_receipt_until_bounded_public_get(self):
        self.one()
        local=receipt.report(_synthetic_db=self.db)
        self.assertTrue(local["attempt_recorded"])
        self.assertFalse(local["independently_visible"])
        calls=[]
        def get(post,comment,*,max_pages):
            calls.append((post,comment,max_pages))
            return "visible_in_public_listing"
        confirmed=receipt.report(public_get=True,auditor=get,_synthetic_db=self.db)
        self.assertTrue(confirmed["independently_visible"])
        self.assertEqual(calls,[(receipt.POST,CID,2)])
        self.assertFalse(confirmed["external_duplicate_excluded"])
        self.assertFalse(confirmed["retry_authorized"])

    def test_missing_id_ambiguous_state_never_retries_or_public_get(self):
        self.one(state="uncertain",comment=None)
        def forbidden(*args,**kwargs):
            raise AssertionError("no public GET without a known comment ID")
        data=receipt.report(public_get=True,auditor=forbidden,_synthetic_db=self.db)
        self.assertEqual(data["public_observation"],"id_unconfirmed")
        self.assertFalse(data["independently_visible"])
        self.assertFalse(data["retry_authorized"])

    def test_same_target_prior_attempt_blocks_independent_acceptance(self):
        self.one()
        self.one(run="20261101T151034Z",mode="auto",
                 state="uncertain",comment=None)
        data=receipt.report(
            public_get=True,
            auditor=lambda *args,**kwargs:"visible_in_public_listing",
            _synthetic_db=self.db)
        self.assertFalse(data["independently_visible"])
        self.assertFalse(data["no_other_attempted_target"])

    def test_unknown_public_api_result_never_claims_success(self):
        self.one()
        data=receipt.report(
            public_get=True,auditor=lambda *args,**kwargs:"unknown",
            _synthetic_db=self.db)
        self.assertFalse(data["independently_visible"])
        self.assertEqual(data["public_observation"],"public_check_unavailable")

    def test_cli_requires_explicit_get_or_check(self):
        self.assertEqual(receipt.main([]),2)
        with patch.object(receipt,"report",return_value={"state":"not_queued"}):
            self.assertEqual(receipt.main(["--check"]),0)


if __name__=="__main__":
    unittest.main()
