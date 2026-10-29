"""Focused offline checks for Bob's read-only queue diagnosis and manual priority."""
from __future__ import annotations
from datetime import datetime, timezone
import importlib.machinery
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src/lib/bob"))
import diagnose_comment_queue as diagnosis
import patch_manual_comment_priority as release


def publisher_module():
    loader = importlib.machinery.SourceFileLoader(
        "bob_test_manual_first_publisher", str(ROOT / "src/bin/bob-moltbook-publisher"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_db(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE publish_settings (name TEXT PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO publish_settings VALUES ('auto_enabled', '0')")
        db.execute("CREATE TABLE publish_jobs (run_id TEXT PRIMARY KEY, approval_sha256 TEXT, "
                   "post_id TEXT, draft_comment TEXT, mode TEXT, state TEXT, created_at TEXT, "
                   "attempted_at TEXT, updated_at TEXT, last_error TEXT)")
        db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                   ("20261029T030000Z","oldhash","post1","old","auto","queued",
                    "2026-10-29T03:00:00+00:00",None,"2026-10-29T03:00:00+00:00",None))
        db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                   ("20261029T040000Z","manualhash","post2","new","manual","queued",
                    "2026-10-29T04:00:00+00:00",None,"2026-10-29T04:00:00+00:00",None))


class ReadOnlyDiagnosis(unittest.TestCase):
    def test_finds_manual_starvation_and_preserves_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            dbfile = Path(folder) / "queue.sqlite3"
            test_db(dbfile)
            with patch.object(diagnosis, "PUBLISHER", Path(folder) / "not-installed"):
                report = diagnosis.diagnose(dbfile, at=datetime(2026,10,29,5,tzinfo=timezone.utc),
                                            paused=False)
            self.assertEqual(report["queued_manual"], 1)
            self.assertEqual(report["queued_auto"], 1)
            self.assertTrue(report["manual_behind_auto"])
            self.assertIn("blocks newer manual", report["reason"])
            with sqlite3.connect(dbfile) as db:
                self.assertEqual(db.execute(
                    "SELECT count(*) FROM publish_jobs WHERE state='queued'").fetchone()[0], 2)

    def test_attempt_cap_is_reported_not_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            dbfile = Path(folder) / "queue.sqlite3"
            test_db(dbfile)
            with sqlite3.connect(dbfile) as db:
                db.execute("UPDATE publish_jobs SET attempted_at='2026-10-29T04:00:00+00:00'")
            with patch.object(diagnosis, "PUBLISHER", Path(folder) / "not-installed"):
                report = diagnosis.diagnose(dbfile, at=datetime(2026,10,29,6,tzinfo=timezone.utc),
                                            paused=False)
            self.assertEqual(report["attempts_today"], 2)
            self.assertEqual(report["daily_limit"], 2)
            self.assertIn("daily comment attempt limit", report["reason"])
            self.assertEqual(report["next_rate_slot_utc"], "2026-10-30T00:00:00+00:00")


class UpdateContracts(unittest.TestCase):
    def test_exact_one_statement_release(self):
        old, new = release.releases()
        self.assertNotEqual(old, new)
        self.assertIn(b"ORDER BY created_at ASC LIMIT 1", old)
        self.assertIn(b"CASE WHEN mode='manual' THEN 0 ELSE 1 END", new)
        self.assertEqual(old.count(b"MAX_DAILY=2"), 1)
        self.assertEqual(new.count(b"MAX_DAILY=2"), 1)
        self.assertEqual(old.count(b"MIN_BETWEEN=timedelta(hours=1)"), 1)
        self.assertEqual(new.count(b"MIN_BETWEEN=timedelta(hours=1)"), 1)


class ManualPriority(unittest.TestCase):
    def test_newer_manual_is_selected_before_disabled_old_auto(self):
        worker = publisher_module()
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE publish_jobs (run_id TEXT PRIMARY KEY, approval_sha256 TEXT, "
                       "post_id TEXT, draft_comment TEXT, mode TEXT, state TEXT, created_at TEXT, "
                       "attempted_at TEXT, updated_at TEXT, last_error TEXT)")
            db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                       ("20261029T030000Z","old","post1","auto content","auto","queued",
                        "2026-10-29T03:00:00Z",None,"2026-10-29T03:00:00Z",None))
            db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                       ("20261029T040000Z","new","post2","manual content","manual","queued",
                        "2026-10-29T04:00:00Z",None,"2026-10-29T04:00:00Z",None))
            with patch.object(worker,"auto_candidates",return_value=0), \
                 patch.object(worker,"load_record",return_value=None), \
                 patch.object(worker,"checkpoint"), \
                 patch.object(worker,"event"), \
                 patch.object(worker,"api",side_effect=AssertionError("unexpected network")):
                result = worker.publisher_step(db)
            self.assertIn("invalid draft blocked", result)
            self.assertEqual(db.execute(
                "SELECT state FROM publish_jobs WHERE mode='manual'").fetchone()[0], "failed")
            self.assertEqual(db.execute(
                "SELECT state FROM publish_jobs WHERE mode='auto'").fetchone()[0], "queued")


if __name__ == "__main__":
    unittest.main()
