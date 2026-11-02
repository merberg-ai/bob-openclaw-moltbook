"""R3 first exact owner-approved source canary preparation: synthetic only."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_r3_canary_approved as report

SEAL="a"*64
NOW=datetime(2026,11,1,19,20,tzinfo=timezone.utc)


def reviewed(**changes):
    settings=dict(
        trusted=True,manual=True,automatic=False,
        run=report.RUN,target=report.POST,proposal_state="proposed",
        seal=SEAL,approval=(SEAL,"approved"),job=None,
        other_attempts=0,now=NOW)
    settings.update(changes)
    return report.verdict(**settings)


class R3CanaryApprovalReadOnlyTests(unittest.TestCase):
    def test_approved_unqueued_exact_source_is_only_a_review_candidate(self):
        result=reviewed()
        self.assertEqual(result["source_run"],report.RUN)
        self.assertEqual(result["target_post"],report.POST)
        self.assertEqual(result["seal_sha256"],SEAL)
        self.assertEqual(result["queue_state"],"none")
        self.assertTrue(result["owner_approval_verified"])
        self.assertFalse(result["canary_send_authorized"])
        self.assertEqual(result["next_gate"],"REVIEW_EXACT_PIN_THEN_SEPARATELY_QUEUE")

    def test_queued_is_still_not_dispatch_authority(self):
        result=reviewed(job=("queued","manual",None))
        self.assertEqual(result["queue_state"],"queued")
        self.assertTrue(result["owner_approval_verified"])
        self.assertFalse(result["canary_send_authorized"])
        self.assertEqual(result["next_gate"],"REVIEW_EXACT_PIN_BEFORE_ANY_PUBLIC_ATTEMPT")

    def test_refuse_untrusted_source_or_seal_or_owner_permission(self):
        for altered in (
            {"trusted":False},{"manual":False},{"automatic":True},
            {"run":"20261101T151034Z"},
            {"target":"11111111-2222-4333-8444-555555555555"},
            {"proposal_state":"cancelled"},
            {"seal":"b"*64},{"seal":"bad"},
            {"approval":None},{"approval":(SEAL,"rejected")},
            {"other_attempts":1},{"now":NOW-timedelta(days=1)},
            {"now":NOW+timedelta(days=8)},
        ):
            with self.subTest(altered=altered):
                result=reviewed(**altered)
                self.assertFalse(result["owner_approval_verified"])
                self.assertIsNone(result["seal_sha256"])
                self.assertFalse(result["canary_send_authorized"])

    def test_other_queue_or_attempt_never_grants_canary_send(self):
        for row in (
            ("sending","manual","2026-11-01T19:00:00+00:00"),
            ("uncertain","manual","2026-11-01T19:00:00+00:00"),
            ("queued","auto",None),
            ("published","manual",None),
        ):
            with self.subTest(row=row):
                result=reviewed(job=row)
                self.assertEqual(result["next_gate"],"STOP_AND_RECONCILE")
                self.assertFalse(result["canary_send_authorized"])

    def test_script_has_no_send_write_or_queue_entrypoint(self):
        text=(ROOT/"scripts/report_r3_canary_approved.py").read_text()
        self.assertIn("mode=ro",text)
        self.assertIn("PRAGMA query_only=ON",text)
        self.assertIn("trusted_manager_boundary",text)
        self.assertIn("_verified_proposal",text)
        self.assertNotIn("db.commit(",text)
        self.assertNotIn("db.execute(\"INSERT",text)
        self.assertNotIn("def publish(",text)
        self.assertNotIn("credential_loader",text)
        self.assertNotIn("http.client",text)

    def test_cli_requires_explicit_read_only_flag(self):
        self.assertEqual(report.main([]),2)
        with patch.object(report,"inspect",return_value=reviewed()):
            self.assertEqual(report.main(["--check"]),0)
        with patch.object(report,"inspect",return_value=reviewed(manual=False)):
            self.assertEqual(report.main(["--check"]),1)


if __name__=="__main__":
    unittest.main()
