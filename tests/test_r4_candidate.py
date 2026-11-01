"""The R4 future release is NOT promoted: source hash and SSL gate review."""
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
    def test_source_scope_is_one_unpromoted_https_release(self):
        audit=source.inspect()
        self.assertEqual(audit["current_unchanged"],"v0.8.0-r3canary1")
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
            (root/"releases/candidates/r4-autonomy1-consolidated.json").write_text(
                json.dumps(candidate))
            with self.assertRaisesRegex(ValueError,"r4_unreviewed_source_target"):
                source.inspect(root=root)
            candidate["from"]="v0.8.0-r3skip1"
            (root/"releases/candidates/r4-autonomy1-consolidated.json").write_text(
                json.dumps(candidate))
            with self.assertRaisesRegex(ValueError,"r4_unsigned_release_chain"):
                source.inspect(root=root)

    def test_unpromoted_manifest_must_not_replace_current(self):
        live=json.loads((ROOT/"releases/current.json").read_text())
        candidate=json.loads((ROOT/
            "releases/candidates/r4-autonomy1-consolidated.json").read_text())
        self.assertEqual(live["release"],"v0.8.0-r3canary1")
        self.assertEqual(candidate["from"],live["release"])
        self.assertNotEqual(candidate["release"],live["release"])
        self.assertNotIn("bob-moltbook-publisher",
                         {f["name"] for f in candidate["files"]})


if __name__=="__main__":
    unittest.main()
