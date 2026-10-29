"""Three focused offline acceptance checks for the queued-release incident repair."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bob_release_updater as updater
import reconcile_bob_queues1_incident as fix


class QueueIncidentRepairSmoke(unittest.TestCase):
    def test_retry_release_has_unique_id_and_original_parent(self):
        manifest = updater.manifest(ROOT)
        self.assertEqual(manifest["release"], fix.RETRY_RELEASE)
        self.assertEqual(manifest["from"], fix.BASELINE_RELEASE)
        self.assertNotEqual(manifest["release"], fix.FIRST_RELEASE)
        self.assertEqual({x["name"] for x in manifest["files"]}, fix.EXPECTED_FILES)

    def test_pinned_updater_patch_only_changes_readiness_and_safe_failure_reporting(self):
        old, new = fix.checked_blob(fix.OLD), fix.checked_blob(fix.NEW)
        self.assertIn(b'BRANCH = "main"', old)
        self.assertIn(b'BRANCH = "main"', new)
        self.assertNotIn(b"def wait_for_health(", old)
        self.assertIn(b"def wait_for_health(", new)
        self.assertIn(b"rollback(journal, auth=auth)", new)
        self.assertIn(b"live_ok(old_registry)", new)

    def test_bounded_probe_and_default_read_only(self):
        with patch.object(updater, "healthy", side_effect=[False, False, True]), \
             patch.object(updater.time, "sleep"):
            self.assertTrue(updater.wait_for_health("fake", seconds=3))
        with patch.object(updater, "healthy", return_value=False):
            self.assertFalse(updater.wait_for_health("fake", seconds=0))
        with patch.object(fix, "plan", return_value=("before", "after", {}, {})), \
             patch.object(fix, "repair", side_effect=AssertionError("unexpected mutation")), \
             patch.object(sys, "argv", ["reconcile_bob_queues1_incident.py"]), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(fix.main(), 0)
        self.assertIn("READY (read-only)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
