"""The exact promoted R4 current manifest must equal the reviewed candidate."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_r4_candidate as source


class R4CandidateReportTests(unittest.TestCase):
    def test_source_scope_is_one_promoted_https_release(self):
        audit=source.inspect()
        self.assertEqual(audit["release_manifest"],"v0.8.0-autonomy1")
        self.assertEqual(audit["previous_installed_release"],"v0.8.0-r3canary1")
        self.assertEqual(audit["promotion_state"],"promoted_exact_candidate")
        self.assertEqual(audit["candidate"],"v0.8.0-autonomy1")
        self.assertEqual(audit["candidate_source_build"],"PASS")
        self.assertTrue(audit["legacy_r3_publisher_not_replaced"])
        self.assertTrue(audit["all_new_auto_modes_compiled_off"])
        self.assertFalse(audit["install_authorized"])
        self.assertFalse(audit["real_social_action_authorized"])
        self.assertFalse(audit["legacy_queue_or_database_modified"])
        self.assertEqual(set(audit["verified_source_hashes"]),source.FILES)

    def test_miswired_path_or_broad_dispatch_source_fails(self):
        with tempfile.TemporaryDirectory(prefix="r4-source-synthetic-") as t:
            root=Path(t)
            # Only copy source directories needed for no-build manifest checks,
            # but failed manifest/path tests return before any source import.
            (root/"releases/candidates").mkdir(parents=True)
            (root/"releases/current.json").write_text(
                (ROOT/"releases/current.json").read_text())
            candidate=json.loads((ROOT/
                "releases/candidates/r4-autonomy1-consolidated.json").read_text())
            candidate["files"][4]["source"]="src/lib/bob/bob_r4_WRONG.py"
            (root/"releases/current.json").write_text(json.dumps(candidate))
            (root/"releases/candidates/r4-autonomy1-consolidated.json").write_text(
                json.dumps(candidate))
            with self.assertRaisesRegex(ValueError,"r4_unreviewed_source_target"):
                source.inspect(root=root)
            candidate["from"]="v0.8.0-r3skip1"
            (root/"releases/candidates/r4-autonomy1-consolidated.json").write_text(
                json.dumps(candidate))
            with self.assertRaisesRegex(ValueError,"r4_unsigned_release_chain"):
                source.inspect(root=root)

    def test_promotion_rejects_any_manifest_drift_even_with_same_release_name(self):
        with tempfile.TemporaryDirectory(prefix="r4-promotion-drift-") as t:
            root=Path(t)
            (root/"releases/candidates").mkdir(parents=True)
            original=json.loads((ROOT/"releases/current.json").read_text())
            candidate=json.loads((ROOT/"releases/candidates/r4-autonomy1-consolidated.json").read_text())
            (root/"releases/candidates/r4-autonomy1-consolidated.json").write_text(json.dumps(candidate))
            for mutation in (
                {"restart_manager":False},
                {"files":candidate["files"][:-1]},
                {"from":"v0.8.0-r3skip1"},
                {"notes":"unreviewed release notes"},
            ):
                with self.subTest(mutation=list(mutation)):
                    (root/"releases/current.json").write_text(
                        json.dumps({**original,**mutation}))
                    with self.assertRaisesRegex(ValueError,"r4_unsigned_release_chain"):
                        source.inspect(root=root)

    def test_promoted_manifest_must_exactly_match_candidate(self):
        live=json.loads((ROOT/"releases/current.json").read_text())
        candidate=json.loads((ROOT/
            "releases/candidates/r4-autonomy1-consolidated.json").read_text())
        self.assertEqual(live,candidate)
        self.assertEqual(live["release"],"v0.8.0-autonomy1")
        self.assertEqual(live["from"],"v0.8.0-r3canary1")
        self.assertTrue(live["restart_manager"])
        # The ONE original publisher is included, not a second worker.
        self.assertIn("bob-moltbook-publisher",
                      {f["name"] for f in candidate["files"]})
        self.assertIn("bob_r4_publisher_adapter.py",
                      {f["name"] for f in candidate["files"]})
        self.assertIn("bob_r4_outbox.py",
                      {f["name"] for f in candidate["files"]})
        self.assertNotIn("bob-r4-publisher",
                         {f["name"] for f in candidate["files"]})


if __name__=="__main__":
    unittest.main()
