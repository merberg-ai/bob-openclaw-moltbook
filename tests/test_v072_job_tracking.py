"""Focused offline v0.7.2 worker-stage tracking acceptance; no workers run."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src/lib/bob"))
sys.path.insert(0, str(ROOT / "webui"))

import bob_job_tracking as tracking
import bob_live_status as status
import bob_status_view as view
import patch_v072_job_tracking as release


class CheckpointContracts(unittest.TestCase):
    def test_private_atomic_checkpoint_and_read(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "progress"
            self.assertTrue(tracking.checkpoint("original", "1234567890abcdef12345678",
                                                "generating", root=root))
            p = root / "original.json"
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            records = tracking.read_checkpoints(root=root)
            self.assertEqual(records[0]["stage"], "generating")
            self.assertNotIn("password", json.dumps(records).lower())

    def test_no_arbitrary_labels_or_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "progress"
            self.assertFalse(tracking.checkpoint("arbitrary", "system", "sending", root=root))
            self.assertFalse(tracking.checkpoint("scout", "../../credentials", "sending", root=root))
            self.assertFalse(tracking.checkpoint("scout", "system", "credentials", root=root))
            self.assertFalse(root.exists())

    def test_stale_running_stage_is_not_presented_as_running(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "progress"
            self.assertTrue(tracking.checkpoint("scout", "20261028T180000Z", "generating", root=root))
            stamp = datetime.now(timezone.utc) + timedelta(minutes=8)
            item = tracking.read_checkpoints(root=root, at=stamp)[0]
            self.assertEqual(item["stage"], "unknown")
            self.assertTrue(item["stale"])

    def test_symlink_checkpoint_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "progress"
            root.symlink_to(Path(folder), target_is_directory=True)
            self.assertFalse(tracking.checkpoint("scout", "system", "queued", root=root))
            self.assertEqual(tracking.read_checkpoints(root=root), [])


class StatusDatabaseContracts(unittest.TestCase):
    def test_queue_read_is_nonmutating_and_excludes_error_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "queue.db"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE publish_jobs (run_id TEXT, state TEXT, created_at TEXT, updated_at TEXT, last_error TEXT)")
                db.execute("CREATE TABLE original_posts (id TEXT, state TEXT, created_at TEXT, updated_at TEXT, last_error TEXT)")
                db.execute("CREATE TABLE original_requests (id TEXT, state TEXT, created_at TEXT, completed_at TEXT, error TEXT)")
                db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?)",
                           ("20261028T180000Z", "cancelled", "2026-10-28T18:00:00+00:00",
                            "2026-10-28T18:01:00+00:00", None))
                db.execute("INSERT INTO original_requests VALUES (?,?,?,?,?)",
                           ("1234567890abcdef12345678", "failed",
                            "2026-10-28T19:00:00+00:00", "2026-10-28T19:02:00+00:00",
                            "SECRETS_MUST_NOT_LEAK"))
                db.commit()
            data = status.queue_snapshot(path)
            self.assertTrue(data["available"])
            self.assertEqual(data["jobs"][0]["state"], "failed")
            self.assertTrue(data["jobs"][0]["has_error"])
            self.assertEqual(data["jobs"][1]["state"], "cancelled")
            self.assertFalse(any(j["automatic_retry"] for j in data["jobs"]))
            self.assertNotIn("SECRETS_MUST_NOT_LEAK", json.dumps(data))
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM original_requests").fetchone()[0], 1)

    def test_ui_escapes_stage_and_error_text(self):
        with patch.object(view, "wrap", side_effect=lambda title, body, route: "<html><head></head><body>" + body + "</body></html>"):
            html = view.page({"services": [], "workers": [
                {"worker": "<img src=x>", "stage": "unknown",
                 "message": "<script>alert(1)</script>", "updated_at": "2026-10-28"}],
                "queue": {"available": True, "jobs": [
                    {"kind": "generation", "state": "failed",
                     "created": "2026-10-28", "updated": "2026-10-28",
                     "has_error": True}]}})
        self.assertIn("bob-worker-grid", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("Error recorded", html)


class WorkerReleaseContracts(unittest.TestCase):
    def test_previous_versions_pinned_and_new_additive(self):
        old, new, manager = release.versions()
        self.assertEqual(set(new) - set(old), {"bob_job_tracking.py"})
        self.assertEqual(len(old), 5)
        self.assertEqual(len(manager), 64)
        for name in ("bob-moltbook-scout", "bob-moltbook-publisher", "bob-original-worker"):
            self.assertIn(b"from bob_job_tracking import checkpoint", new[name])
            self.assertNotIn(b"from bob_job_tracking import checkpoint", old[name])
        self.assertIn(b"read_checkpoints", new["bob_live_status.py"])
        self.assertNotIn(b"read_checkpoints", old["bob_live_status.py"])

    def test_old_worker_code_still_retains_publication_guard(self):
        _, new, _ = release.versions()
        publisher = new["bob-moltbook-publisher"]
        self.assertIn(b"MAX_DAILY=2", publisher)
        self.assertIn(b"no automatic retry", publisher.lower())
        self.assertIn(b"state='sending'", publisher)
        original = new["bob-original-worker"]
        self.assertIn(b"state='sending'", original)
        self.assertIn(b"add_draft(db,rid,title,body)", original)


if __name__ == "__main__":
    unittest.main()
