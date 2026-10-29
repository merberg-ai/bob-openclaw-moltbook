"""v0.7.2 bounded read-only status contract tests."""
from pathlib import Path
import sys
import unittest
import sqlite3
import tempfile
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/lib/bob"))
sys.path.insert(0, str(ROOT / "scripts"))
import bob_live_status as status
import build_v072_settings_candidate as builder

class StatusContracts(unittest.TestCase):
    def test_fixed_allowlist(self):
        with self.assertRaises(ValueError):
            status.unit_state("arbitrary.service")
    def test_no_systemd_mutations(self):
        with patch.object(status.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "active\n"
            self.assertEqual(status.unit_state("openclaw-gateway.service"), "running")
            self.assertEqual(run.call_args.args[0][:3], ["systemctl", "--user", "is-active"])
    def test_stalled_systemd_is_unknown(self):
        with patch.object(status.subprocess, "run", side_effect=status.subprocess.TimeoutExpired("systemctl", 1)):
            self.assertEqual(status.unit_state("bob-moltbook-scout.service"), "unknown")
    def test_page_and_api_routes(self):
        manager, navigation = builder.build()
        self.assertIn(b'elif self.path == "/system/status"', manager)
        self.assertIn(b'elif self.path == "/api/system/status"', manager)
        self.assertIn(b'("/system/status", "System status", "System status")', navigation)
    def test_queue_states_are_real_and_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            dbpath = Path(temp) / "queue.sqlite3"
            with sqlite3.connect(dbpath) as db:
                db.execute("CREATE TABLE publish_jobs (state TEXT, created_at TEXT)")
                db.execute("CREATE TABLE original_posts (state TEXT, created_at TEXT)")
                db.execute("CREATE TABLE original_requests (state TEXT, created_at TEXT)")
                db.execute("INSERT INTO publish_jobs VALUES ('awaiting_verification','2026-10-28T18:00:00Z')")
                db.execute("INSERT INTO original_requests VALUES ('queued','2026-10-28T18:01:00Z')")
                db.commit()
            result = status.queue_snapshot(dbpath)
            self.assertTrue(result["available"])
            self.assertEqual([x["state"] for x in result["jobs"]], ["queued", "awaiting_verification"])
            with sqlite3.connect(dbpath) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0], 1)

    def test_missing_queue_is_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(status.queue_snapshot(Path(temp) / "missing.db")["available"])

    def test_labels_are_not_fake_job_progress(self):
        self.assertEqual(len(status.UNITS), 4)
        self.assertNotIn("generating", status.snapshot.__code__.co_consts)
if __name__ == "__main__":
    unittest.main()
