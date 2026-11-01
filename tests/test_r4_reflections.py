"""R4 opinions only come from signed, source-linked real Bob proposals."""
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_reflections as reflections


class R4SealedReflectionTests(unittest.TestCase):
    def test_real_sealed_reason_is_labeled_opinion_not_confirmed_fact(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"queue.sqlite3"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE example(id INTEGER)")
            owner=types.ModuleType("bob_r313d_owner")
            owner.trusted_manager_boundary=lambda conn: True
            owner.control_state=lambda conn: {"schema":"ready"}
            owner.recent_proposals=lambda conn,source,limit: [{
                "run":"20261101T151033Z","title":"The gate works",
                "reason":"Stale decisions need an age threshold",
                "status":"published"}]
            package=types.ModuleType("bob_r313d_package")
            package.load_verified=lambda:"verified_registry_archive"
            with patch.dict(sys.modules,{"bob_r313d_owner":owner,
                                         "bob_r313d_package":package}):
                rows=reflections.reasons(path=db,source=Path(tmp),limit=2)
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]["source_run"],"20261101T151033Z")
            self.assertEqual(rows[0]["reason"],
                             "Stale decisions need an age threshold")
            self.assertEqual(rows[0]["confidence"],
                             "expressed_by_bob_not_owner_confirmed")

    def test_no_source_verification_means_no_claimed_opinion(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"queue.sqlite3"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE example(id INTEGER)")
            owner=types.ModuleType("bob_r313d_owner")
            owner.trusted_manager_boundary=lambda conn: False
            owner.control_state=lambda conn: {"schema":"ready"}
            owner.recent_proposals=lambda *args,**kwargs:self.fail(
                "Untrusted database must not show Bob's reasons")
            package=types.ModuleType("bob_r313d_package")
            package.load_verified=lambda:"verified_registry_archive"
            with patch.dict(sys.modules,{"bob_r313d_owner":owner,
                                         "bob_r313d_package":package}):
                self.assertEqual(reflections.reasons(path=db,source=Path(tmp)),[])
        self.assertEqual(reflections.reasons(path=Path("/never-present.db")),[])


if __name__=="__main__":
    unittest.main()
