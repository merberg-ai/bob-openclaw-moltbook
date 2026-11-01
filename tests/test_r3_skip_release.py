"""One signed, proposal-only R3 skip repair. Fully synthetic offline tests."""
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
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src")]
import bob_release_updater as upd
import build_r313d_off_package as historical
import build_r3_skip_package as repaired
import report_r3_skip_installed as report
from bob_v08 import r313d_producer as producer


class R3Skip1ReleaseTests(unittest.TestCase):
    def test_exact_manifest_and_backward_chain(self):
        candidate=json.loads((ROOT/"releases/candidates/r3-skip1-offfirst.json").read_text())
        # Historic accepted skip1 candidate stays immutable after canary promotion.
        self.assertEqual(candidate["release"],"v0.8.0-r3skip1")
        self.assertEqual(candidate["release"],"v0.8.0-r3skip1")
        self.assertEqual(candidate["from"],"v0.8.0-r3format1")
        self.assertFalse(candidate["restart_manager"])
        self.assertEqual(
            {item["name"] for item in candidate["files"]},
            {"bob-release-updater","bobctl","bob_r3_package.pyz"})
        self.assertEqual(upd.manager_transport(candidate["release"]),"https")
        self.assertEqual(upd.manager_transport(candidate["from"]),"https")
        self.assertNotIn("bob-moltbook-publisher",str(candidate["files"]))
        self.assertNotIn("bob-activity-manager",str(candidate["files"]))
        self.assertNotIn("bob-moltbook-scout",str(candidate["files"]))
        for file in candidate["files"]:
            self.assertTrue(upd.release_bytes(ROOT,file))

    def test_signed_package_is_deterministic_and_changes_only_producer(self):
        previous,old_launcher=historical.build()
        changed,launcher=repaired.build()
        self.assertEqual(changed,repaired.build()[0])
        self.assertEqual(old_launcher,launcher)
        self.assertNotEqual(previous,changed)
        with ZipFile(BytesIO(previous)) as a,ZipFile(BytesIO(changed)) as b:
            self.assertEqual(a.namelist(),b.namelist())
            changed_paths={name for name in a.namelist()
                           if a.read(name)!=b.read(name)}
            self.assertEqual(changed_paths,{"bob_v08/r313d_producer.py"})
            old=a.read("bob_v08/r313d_producer.py")
            new=b.read("bob_v08/r313d_producer.py")
            self.assertNotIn(b"record_verified_skip(",old)
            self.assertIn(b"def record_verified_skip(",new)
            self.assertIn(b"r313d_skip",new)
            self.assertIn(b"NO_PRODUCTION_DISPATCH = True",new)
        self.assertTrue(producer.NO_PRODUCTION_DISPATCH)

    def test_new_release_only_uses_existing_fail_closed_diagnostic_preflight(self):
        code=(ROOT/"scripts/bob_release_updater.py").read_text()
        self.assertIn('"v0.8.0-r3skip1","v0.8.0-r3canary1") and not preflight_r3_diagnostics_only()',code)
        handoff=(ROOT/"scripts/r3_service_handoff.py").read_text()
        self.assertIn('"v0.8.0-r3skip1") or not updater.live_ok(state)',handoff)
        self.assertIn('("bob_r313c_adapter.py",("R313C_REAL_DISPATCH",False))',handoff)
        self.assertIn('("bob_r313d_owner.py",("R3_AUTO_UI_COMPILED_OFF",True))',handoff)

    def test_readonly_installed_report_checks_exact_reviewed_source(self):
        with tempfile.TemporaryDirectory(prefix="r3skip-installed-") as temp:
            root=Path(temp)
            archive=root/"bob_r3_package.pyz"
            archive.write_bytes(repaired.build()[0])
            with patch.object(report.upd,"BIN",root),patch.object(
                    report,"_verified_release",return_value=True):
                self.assertTrue(report._package())
                archive.write_bytes(historical.build()[0])
                self.assertFalse(report._package())
        ok=report.inspect(
            owner=lambda:True, installed=lambda:True,
            package=lambda:True,health=lambda:True,
            controls=lambda:True,units=lambda:True)
        self.assertEqual(ok["acceptance"],"PASS")
        self.assertFalse(ok["r3_real_publication_authorized"])
        self.assertFalse(ok["host_or_database_changed"])
        self.assertEqual(ok["moltbook_requests"],0)
        for key in ("owner","installed","package","health","controls","units"):
            kwargs={i:lambda:True for i in
                    ("owner","installed","package","health","controls","units")}
            kwargs[key]=lambda:False
            self.assertEqual(report.inspect(**kwargs)["acceptance"],"NOT_VERIFIED")


if __name__=="__main__":
    unittest.main()
