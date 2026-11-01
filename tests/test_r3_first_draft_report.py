"""Offline, synthetic and side-effect-free first-draft readout contract."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "r3_first_draft_report", ROOT / "scripts/report_r3_first_draft.py")
report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)


class ReportTests(unittest.TestCase):
    def entry(self, **kw):
        return dict(run="20261101T034500Z", status="proposed",
                    approval="none", queue_state="none",
                    attempted=False, text="do not print me",
                    **kw)

    def test_skipped_is_not_a_proposal_or_canary(self):
        item = self.entry()
        item["status"] = "skipped"
        result = report.summarize({"schema": "ready", "manual": False}, [item])
        self.assertEqual(result["unreviewed"], 0)
        self.assertEqual(result["next_gate"], "await_natural_proposed_decision")
        self.assertFalse(result["public_canary_authorized"])
        self.assertNotIn("do not print me", str(result))

    def test_exact_source_linked_review_and_queue_gates_are_separate(self):
        item = self.entry()
        result = report.summarize({"schema": "ready", "manual": False}, [item])
        self.assertEqual(result["unreviewed"], 1)
        self.assertIn("must_review", result["next_gate"])
        item["approval"] = "approved"
        result = report.summarize({"schema": "ready", "manual": True}, [item])
        self.assertEqual(result["approved_not_queued"], 1)
        self.assertIn("may_queue", result["next_gate"])
        item["status"] = "queued"
        item["queue_state"] = "queued"
        result = report.summarize({"schema": "ready", "manual": True}, [item])
        self.assertEqual(result["queued_unattempted"], 1)
        self.assertFalse(result["public_canary_authorized"])
        self.assertIn("source_release", result["next_gate"])

    def test_uncertain_or_attempted_prevents_new_canary(self):
        item = self.entry()
        item["status"] = "uncertain"
        item["queue_state"] = "uncertain"
        item["attempted"] = True
        result = report.summarize({"schema": "ready"}, [item])
        self.assertEqual(result["attempt_recorded"], 1)
        self.assertIn("reconcile_attempt", result["next_gate"])

    def test_untrusted_schema_suppresses_even_apparently_valid_rows(self):
        item = self.entry()
        result = report.summarize({"schema": "invalid", "manual": True}, [item])
        self.assertEqual(result["verified_proposals"], 0)
        self.assertIsNone(result["candidate_run"])
        self.assertFalse(result["manual_owner_mode"])


if __name__ == "__main__":
    unittest.main()
