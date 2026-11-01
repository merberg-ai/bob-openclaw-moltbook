"""Offline R3 format1 bundle/acceptance regression. No host service or network."""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src")]
import bob_release_updater as updater
import report_r3_format_installed as report
import build_r313d_off_package as build


class R3Format1ReleaseTests(TestCase):
    def test_three_file_signed_https_release_does_not_change_publisher(self):
        current=json.loads((ROOT/"releases/current.json").read_text())
        expected=json.loads((ROOT/"releases/candidates/r3-format1-offfirst.json").read_text())
        self.assertEqual(current,expected)
        self.assertEqual(current["release"],"v0.8.0-r3format1")
        self.assertEqual(current["from"],"v0.8.0-r3diag1")
        self.assertFalse(current["restart_manager"])
        names={x["name"] for x in current["files"]}
        self.assertEqual(names,{"bob-release-updater","bobctl","bob_r3_package.pyz"})
        self.assertEqual(updater.manager_transport(current["release"]),"https")
        self.assertEqual(updater.manager_transport(current["from"]),"https")
        self.assertFalse(names & {"bob-activity-manager","bob-moltbook-publisher",
                                  "bob-moltbook-scout","bob-r3-publisher"})
        for item in current["files"]:
            self.assertTrue(updater.release_bytes(ROOT,item))

    def test_report_marker_proves_new_source_in_synthetic_archive(self):
        with tempfile.TemporaryDirectory(prefix="r3-format-fixture-") as temp:
            folder=Path(temp)
            (folder/"bob_r3_package.pyz").write_bytes(build.build()[0])
            with patch.object(report.updater,"BIN",folder),patch.object(
                    report,"_signed",return_value=True):
                self.assertTrue(report._exact_package())
            (folder/"bob_r3_package.pyz").write_bytes(b"corrupted")
            with patch.object(report.updater,"BIN",folder),patch.object(
                    report,"_signed",return_value=True):
                self.assertFalse(report._exact_package())

    def test_fail_closed_report_without_creating_any_public_job(self):
        kwargs=dict(owner=lambda:True,installed=lambda:True,
                    package=lambda:True,health=lambda:True,
                    controls=lambda:True,units=lambda:True)
        ok=report.inspect(**kwargs)
        self.assertEqual(ok["acceptance"],"PASS")
        self.assertFalse(ok["host_or_database_changed"])
        self.assertFalse(ok["r3_real_publication_authorized"])
        self.assertEqual(ok["moltbook_requests"],0)
        for key in kwargs:
            with self.subTest(probe=key):
                modified=dict(kwargs)
                modified[key]=lambda:False
                self.assertEqual(report.inspect(**modified)["acceptance"],
                                 "NOT_VERIFIED")

    def test_shape_invalid_never_makes_model_source_a_publisher(self):
        from bob_v08 import r313d_producer as producer
        from bob_v08.core import Observation
        self.assertTrue(producer.NO_PRODUCTION_DISPATCH)
        obs=Observation("20261101T014755Z","11111111-2222-3333-4444-555555555555",
                        "untrusted author","untrusted title","untrusted excerpt",
                        "a"*64,"b"*64,"")
        text=producer.r3_decision_prompt(obs)
        self.assertIn('"type":"skip"',text)
        self.assertIn('"source_run":"20261101T014755Z"',text)
        self.assertEqual(producer._shape_reason('{"bad":"private"}'),
                         "shape_missing_and_extra_fields")
        self.assertFalse(producer.ProposalResult(
            "refused","decision_shape_missing_fields").dispatch_authorized)


if __name__=="__main__":
    main()
