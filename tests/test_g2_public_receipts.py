"""Synthetic G2 public-receipt audit tests. No live database or Internet."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import report_g2_public_receipts as g2

POST_A = "a9ccf436-c5d5-4849-af92-843670ab8271"
POST_B = "b9ccf436-c5d5-4849-af92-843670ab8271"
RECEIPT_A = "c9ccf436-c5d5-4849-af92-843670ab8271"
RECEIPT_B = "d9ccf436-c5d5-4849-af92-843670ab8271"


class G2ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "queue.sqlite3"
        with sqlite3.connect(self.db) as con:
            con.execute(
                "CREATE TABLE publish_jobs ("
                "run_id TEXT, post_id TEXT, comment_id TEXT, "
                "state TEXT, attempted_at TEXT)")

    def insert(self, run, post=POST_A, receipt=RECEIPT_A,
               state="published", stamp="2026-10-31T00:01:00+00:00"):
        with sqlite3.connect(self.db) as con:
            con.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?)",
                        (run, post, receipt, state, stamp))

    def test_one_public_receipt_and_explicit_not_proof_of_no_duplicates(self):
        self.insert("20261031T000100Z")
        calls = []
        def visible(post, receipt, *, max_pages):
            calls.append((post, receipt, max_pages))
            return "visible_in_public_listing"
        report = g2.reconcile(self.db, public_get=True, check=visible)
        self.assertEqual(calls, [(POST_A, RECEIPT_A, 2)])
        self.assertEqual(report["attempts_total"], 1)
        self.assertEqual(report["status"], "known_receipts_visible")
        self.assertTrue(report["known_receipts_all_visible"])
        self.assertFalse(report["external_duplicate_posting_excluded"])
        self.assertFalse(report["original_posts_audited"])
        self.assertFalse(report["database_or_systemd_changed"])
        self.assertEqual(report["external_write_requests"], 0)
        self.assertFalse(report["r3_real_publishing_authorized"])

    def test_no_public_get_by_default(self):
        self.insert("20261031T000100Z")
        with patch.object(g2.visibility, "audit_one") as public_get:
            report = g2.reconcile(self.db)
        public_get.assert_not_called()
        self.assertEqual(report["status"], "review_required")
        self.assertFalse(report["public_get_enabled"])
        self.assertEqual(report["db_unchanged_during_get"], "not_checked")

    def test_missing_receipt_after_attempt_cannot_be_cleared(self):
        self.insert("20261031T000100Z", receipt=None, state="failed")
        with patch.object(g2.visibility, "audit_one") as getter:
            report = g2.reconcile(self.db, public_get=True)
        getter.assert_not_called()
        self.assertEqual(report["local_review_flags"]["missing_or_invalid_receipt_id"], 1)
        self.assertEqual(report["saved_receipt_ids"], 0)
        self.assertFalse(report["known_receipts_all_visible"])

    def test_unknown_and_sending_states_flagged(self):
        self.insert("20261031T000100Z", state="sending")
        self.insert("20261031T000200Z", post=POST_B, receipt=RECEIPT_B,
                    state="wild_state", stamp="2026-10-31T00:02:00+00:00")
        r = g2.reconcile(self.db, public_get=True,
                         check=lambda *args, **kwargs: "visible_in_public_listing")
        self.assertEqual(r["local_review_flags"]["unresolved_attempt_state"], 1)
        self.assertEqual(r["local_review_flags"]["unrecognized_state"], 1)
        self.assertFalse(r["known_receipts_all_visible"])

    def test_repeat_target_attempts_are_flags_not_auto_duplicate_claims(self):
        self.insert("20261031T000100Z")
        self.insert("20261031T000200Z", receipt=RECEIPT_B,
                    stamp="2026-10-31T00:02:00+00:00")
        r = g2.reconcile(self.db)
        self.assertEqual(r["local_review_flags"]["repeat_attempted_target_groups"], 1)
        self.assertFalse(r["external_duplicate_posting_excluded"])

    def test_same_comment_id_across_jobs_flags_review(self):
        self.insert("20261031T000100Z")
        self.insert("20261031T000200Z", post=POST_B,
                    stamp="2026-10-31T00:02:00+00:00")
        r = g2.reconcile(self.db)
        self.assertEqual(r["local_review_flags"]["reused_comment_receipt_ids"], 1)

    def test_public_missing_incomplete_and_unavailable_fail_closed(self):
        self.insert("20261031T000100Z")
        for reason in ("not_observed_in_public_listing", "scan_incomplete",
                       "public_check_unavailable", "id_unconfirmed",
                       "unexpected_response"):
            with self.subTest(reason=reason):
                r = g2.reconcile(self.db, public_get=True,
                                 check=lambda *args, **kwargs: reason)
                self.assertEqual(r["status"], "review_required")
                self.assertFalse(r["known_receipts_all_visible"])

    def test_public_get_exceptions_are_not_retried(self):
        self.insert("20261031T000100Z")
        def broken(*args, **kwargs):
            raise TimeoutError("test")
        r = g2.reconcile(self.db, public_get=True, check=broken)
        self.assertEqual(r["public_observation_counts"]["public_check_unavailable"], 1)

    def test_race_during_public_get_blocks_complete_result(self):
        self.insert("20261031T000100Z")
        def move(*args, **kwargs):
            with sqlite3.connect(self.db) as con:
                con.execute("UPDATE publish_jobs SET state='verified_unconfirmed'")
            return "visible_in_public_listing"
        r = g2.reconcile(self.db, public_get=True, check=move)
        self.assertFalse(r["db_unchanged_during_get"])
        self.assertFalse(r["known_receipts_all_visible"])

    def test_scope_truncated_never_claims_all_receipts(self):
        self.insert("20261031T000100Z")
        self.insert("20261031T000200Z", post=POST_B, receipt=RECEIPT_B,
                    stamp="2026-10-31T00:02:00+00:00")
        with patch.object(g2, "MAX_JOBS", 1):
            r = g2.reconcile(self.db, public_get=True,
                             check=lambda *args, **kwargs: "visible_in_public_listing")
        self.assertTrue(r["attempts_truncated"])
        self.assertFalse(r["known_receipts_all_visible"])

    def test_schema_missing_or_path_symlink_refuses(self):
        with sqlite3.connect(self.db) as con:
            con.execute("DROP TABLE publish_jobs")
        with self.assertRaises(ValueError):
            g2.reconcile(self.db)
        target = Path(self.tmp.name) / "other.sqlite3"
        target.write_text("not a database")
        link = Path(self.tmp.name) / "link.sqlite3"
        link.symlink_to(target)
        with self.assertRaises(ValueError):
            g2.reconcile(link)

    def test_cli_owner_and_unknown_flags_fail_closed(self):
        with patch.object(g2, "_owner", return_value=False), redirect_stdout(StringIO()):
            self.assertEqual(g2.main(["--public-get"]), 1)
        with patch.object(g2, "_owner", return_value=True), \
             patch.object(g2, "reconcile", return_value={
                 "status": "review_required", "attempts_total": 23,
                 "attempts_inspected": 23, "attempts_truncated": False,
                 "saved_receipt_ids": 0, "local_review_flags": {},
                 "public_get_enabled": True, "public_observation_counts": {},
                 "db_unchanged_during_get": True,
                 "known_receipts_all_visible": False}) as function, \
             redirect_stdout(StringIO()):
            self.assertEqual(g2.main(["--public-get"]), 0)
            function.assert_called_once_with(public_get=True)
            with self.assertRaises(SystemExit):
                g2.main(["--install"])

if __name__ == "__main__":
    unittest.main()
