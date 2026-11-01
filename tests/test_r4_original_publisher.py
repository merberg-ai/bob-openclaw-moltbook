"""The existing credentialed Bob publisher remains sole writer; R4 is Off."""
from pathlib import Path
import importlib.machinery
import importlib.util
import sqlite3
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))


def publisher():
    loader=importlib.machinery.SourceFileLoader(
        "bob_r4_original_publisher_synthetic",
        str(ROOT/"src/bin/bob-moltbook-publisher"))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    mod=importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class R4OriginalPublisherGateTests(unittest.TestCase):
    def test_one_original_publisher_never_calls_r4_api_when_off(self):
        p=publisher()
        self.assertTrue(p.R4_SINGLE_PUBLISHER_COMPILED_OFF)
        self.assertFalse(p.R313C_INTEGRATION_COMPILED_OFF)
        db=sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        p.auto_candidates=lambda db: 0
        p.legacy_queue_head=lambda db: None
        p.held_r3_count=lambda db: 0
        p.record_publisher_skip=lambda *args:None
        p.api=lambda *args,**kwargs:self.fail("R4 must never call Moltbook")
        p.api_key=lambda:self.fail("R4 must not request credentials")
        # Test R4 Off in isolation. R3 verified canary has its own guards.
        p.R313C_INTEGRATION_COMPILED_OFF=True
        self.assertEqual(p.publisher_step(db),"no queued publications")
        self.assertTrue(p.R4_SINGLE_PUBLISHER_COMPILED_OFF)

    def test_single_original_api_owner_and_disabled_adapter_sources(self):
        source=(ROOT/"src/bin/bob-moltbook-publisher").read_text()
        adapter=(ROOT/"src/lib/bob/bob_r4_publisher_adapter.py").read_text()
        self.assertEqual(source.count("def api("),1)
        self.assertEqual(source.count("def api_key("),1)
        self.assertIn("R4_SINGLE_PUBLISHER_COMPILED_OFF = True",source)
        self.assertIn("if not R4_SINGLE_PUBLISHER_COMPILED_OFF:",source)
        self.assertIn("R4_REAL_DISPATCH_COMPILED_OFF=True",adapter)
        self.assertNotIn("def api_key(",adapter)
        self.assertNotIn("urllib.request",adapter)
        self.assertNotIn("credentials.json",adapter)


if __name__=="__main__":
    unittest.main()
