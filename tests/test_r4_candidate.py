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
    def test_historical_r4_source_audit_refuses_obsolete_promotion(self):
        # R4 autonomy1's original audit does NOT claim to audit format1.
        historic=json.loads((ROOT/
            "releases/candidates/r4-autonomy1-consolidated.json").read_text())
        old_patch=json.loads((ROOT/
            "releases/candidates/r4-propose1-one-shot.json").read_text())
        current=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(historic["release"],"v0.8.0-autonomy1")
        self.assertEqual(old_patch["from"],historic["release"])
        intermediate=json.loads((ROOT/
            "releases/candidates/r4-format1-json-reliability.json").read_text())
        self.assertEqual(intermediate["from"],old_patch["release"])
        self.assertEqual(current["from"],intermediate["release"])
        self.assertEqual(current["release"],"v0.8.0-r4schedule1")
        with self.assertRaisesRegex(ValueError,"r4_unsigned_release_chain"):
            source.inspect()

    def test_miswired_path_or_broad_dispatch_source_fails(self):
        with tempfile.TemporaryDirectory(prefix="r4-source-synthetic-") as t:
            root=Path(t)
            # Only copy source directories needed for no-build manifest checks,
            # but failed manifest/path tests return before any source import.
            (root/"releases/candidates").mkdir(parents=True)
            (root/"releases/current.json").write_text(
                (ROOT/"releases/candidates/r4-propose1-one-shot.json").read_text())
            candidate=json.loads((ROOT/
                "releases/candidates/r4-autonomy1-consolidated.json").read_text())
            candidate["files"][4]["source"]="src/lib/bob/bob_r4_WRONG.py"
            (root/"releases/candidates/r4-propose1-one-shot.json").write_text(
                (ROOT/"releases/candidates/r4-propose1-one-shot.json").read_text())
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
            original=json.loads((ROOT/
                "releases/candidates/r4-propose1-one-shot.json").read_text())
            candidate=json.loads((ROOT/"releases/candidates/r4-autonomy1-consolidated.json").read_text())
            (root/"releases/candidates/r4-autonomy1-consolidated.json").write_text(json.dumps(candidate))
            (root/"releases/candidates/r4-propose1-one-shot.json").write_text((ROOT/"releases/candidates/r4-propose1-one-shot.json").read_text())
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

    def test_current_schedule_patch_chain_references_immutable_old_r4_candidate(self):
        live=json.loads((ROOT/"releases/current.json").read_text())
        offer=json.loads((ROOT/
            "releases/candidates/r4-schedule1-offfirst.json").read_text())
        format1=json.loads((ROOT/
            "releases/candidates/r4-format1-json-reliability.json").read_text())
        previous=json.loads((ROOT/
            "releases/candidates/r4-propose1-one-shot.json").read_text())
        base=json.loads((ROOT/
            "releases/candidates/r4-autonomy1-consolidated.json").read_text())
        self.assertEqual(live,offer)
        self.assertEqual(live["release"],"v0.8.0-r4schedule1")
        self.assertEqual(live["from"],format1["release"])
        self.assertEqual(format1["from"],previous["release"])
        self.assertEqual(previous["from"],base["release"])
        self.assertEqual(base["from"],"v0.8.0-r3canary1")
        self.assertTrue(live["restart_manager"])
        self.assertEqual({x["name"] for x in live["files"]},{
            "bob-release-updater","bobctl","bob_r4_installed_gate.py",
            "bob_r4_schedule.py","bob-r4-schedule","bob_r4_web.py"})
        self.assertNotIn("bob-moltbook-publisher",
                         {x["name"] for x in live["files"]})
        self.assertNotIn("bob-r4-publisher",
                         {x["name"] for x in live["files"]})
        self.assertIn("bob-moltbook-publisher",
                      {f["name"] for f in base["files"]})
        self.assertIn("bob_r4_publisher_adapter.py",
                      {f["name"] for f in base["files"]})


if __name__=="__main__":
    unittest.main()
