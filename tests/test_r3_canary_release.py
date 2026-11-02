"""One signed, manually armed, exact-target R3 canary release: offline only."""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src"),str(ROOT/"src/lib/bob")]
import bob_release_updater as upd
import build_r313d_off_package as format1
import build_r3_skip_package as skip1
import build_r3_canary_package as canary
import report_r3_canary_installed as report
import bob_r313c_adapter as adapter


class ExactCanaryReleaseTests(unittest.TestCase):
    def test_reviewed_historical_r3_canary_is_still_exact_seven_file_scope(self):
        live=json.loads((ROOT/"releases/current.json").read_text())
        m=json.loads((ROOT/"releases/candidates/r3-canary1-exact-manual.json").read_text())
        self.assertEqual(live,json.loads((ROOT/"releases/candidates/r4-propose1-one-shot.json").read_text()))
        self.assertEqual(live["from"],"v0.8.0-autonomy1")
        previous=json.loads((ROOT/"releases/candidates/r4-autonomy1-consolidated.json").read_text())
        self.assertEqual(previous["from"],m["release"])
        self.assertEqual(m["release"],"v0.8.0-r3canary1")
        self.assertEqual(m["from"],"v0.8.0-r3skip1")
        self.assertFalse(m["restart_manager"])
        self.assertEqual({i["name"] for i in m["files"]},{
            "bob-release-updater","bobctl","bob_r3_package.pyz",
            "bob_r3_canary_lock.py","bob_r313c_adapter.py",
            "bob-moltbook-publisher","bob-r3-canary-arm"})
        self.assertNotIn("bob-activity-manager",{x["name"] for x in m["files"]})
        self.assertNotIn("bob-moltbook-scout",{x["name"] for x in m["files"]})
        self.assertNotIn("bob_r313d_owner.py",{x["name"] for x in m["files"]})
        self.assertEqual(upd.manager_transport(m["release"]),"https")
        self.assertEqual(upd.manager_transport(m["from"]),"https")
        for item in m["files"]:
            self.assertTrue(upd.release_bytes(ROOT,item))

    def test_format1_and_skip1_historical_archives_remain_unchanged(self):
        old,_=format1.build()
        skip,_=skip1.build()
        exact,_=canary.build()
        self.assertEqual(exact,canary.build()[0])
        self.assertNotEqual(old,skip)
        self.assertNotEqual(skip,exact)
        with ZipFile(BytesIO(old)) as a, ZipFile(BytesIO(skip)) as b, \
                ZipFile(BytesIO(exact)) as c:
            self.assertEqual(a.namelist(),b.namelist())
            self.assertEqual(b.namelist(),c.namelist())
            self.assertEqual({name for name in a.namelist()
                              if a.read(name)!=b.read(name)},
                             {"bob_v08/r313d_producer.py"})
            self.assertEqual({name for name in b.namelist()
                              if b.read(name)!=c.read(name)},
                             {"bob_v08/r313c_candidate.py"})
            self.assertIn(b"def record_verified_skip(",
                          c.read("bob_v08/r313d_producer.py"))
            self.assertIn(b"exact_canary_run_changed",
                          c.read("bob_v08/r313c_candidate.py"))

    def test_publisher_has_only_one_source_locked_dispatch_branch(self):
        main=(ROOT/"src/bin/bob-moltbook-publisher").read_text()
        adapter_code=(ROOT/"src/lib/bob/bob_r313c_adapter.py").read_text()
        arm=(ROOT/"src/bin/bob-r3-canary-arm").read_text()
        self.assertIn("R313C_INTEGRATION_COMPILED_OFF = False",main)
        self.assertIn("R313C_REAL_DISPATCH = False",adapter_code)
        self.assertIn("R3_EXACT_CANARY_COMPILED = True",adapter_code)
        self.assertIn("return marker_valid(now=datetime.now(timezone.utc))",adapter_code)
        self.assertIn("installed_canary_ready",adapter_code)
        self.assertIn("exact_canary_run=head",adapter_code)
        self.assertIn("still_pinned_for_send",adapter_code)
        self.assertIn("REQUIRED_FILES",arm)
        self.assertIn("os.O_EXCL",arm)
        self.assertIn("sys.stdin.isatty()",arm)
        self.assertNotIn("api_key(",arm)
        self.assertNotIn("http.client",arm)
        self.assertFalse(adapter.production_dispatch_enabled())

    def test_offline_signed_installed_report_never_arms_or_writes(self):
        good=report.inspect(owner=lambda:True,scope=lambda:True,
                            health=lambda:True,controls=lambda:True,
                            units=lambda:True)
        self.assertEqual(good["acceptance"],"PASS")
        self.assertFalse(good["armed_by_install"])
        self.assertFalse(good["canary_public_post_sent_by_report"])
        self.assertFalse(good["publisher_or_schema_migrated"])
        for broken in ("owner","scope","health","controls","units"):
            callbacks={key:lambda:True for key in
                       ("owner","scope","health","controls","units")}
            callbacks[broken]=lambda:False
            self.assertEqual(report.inspect(**callbacks)["acceptance"],
                             "NOT_VERIFIED")
        with tempfile.TemporaryDirectory(prefix="r3canary-package-") as tmp:
            base=Path(tmp)
            (base/"bob_r3_package.pyz").write_bytes(canary.build()[0])
            # Only the installed R3 ZIP bytes are being patched. No live host.
            with patch.object(report.upd,"BIN",base), \
                    patch.object(report,"_literal_constant",return_value=False), \
                    patch.object(report.upd,"registry",return_value={
                        "release":report.RELEASE,"files":{x:"digest"
                        for x in report.EXPECTED}}), \
                    patch.object(report.upd,"live_ok",return_value=True):
                self.assertFalse(report._signed_scope())


if __name__=="__main__":
    unittest.main()
