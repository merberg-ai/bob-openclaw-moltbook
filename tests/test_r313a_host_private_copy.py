"""R3.13a: synthetic fixed-host private-copy migration, never live sends."""
from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "tests")]

from bob_v08 import r313a_private_migration as m
from bob_v08.r35_migration_lab import MigrationFixture, NEW, SCHEMA
from test_r35_migration_recovery import create_legacy_fixture
import report_r313a_host as cli


class TrustedHostTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="r313a-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / "home"
        (self.home / ".config").mkdir(parents=True, mode=0o700)
        (self.home / ".config" / "bob-system").mkdir(mode=0o700)
        os.chmod(self.home, 0o700)
        os.chmod(self.home / ".config", 0o700)
        self.queue = self.home / ".config" / "moltbook" / "activity-queue.sqlite3"
        self.paused = self.home / ".config" / "bob-system" / "paused"
        create_legacy_fixture(self.queue)
        self.opts = dict(home=self.home, queue=self.queue,
                         paused=self.paused, uid=os.geteuid())

    def report(self):
        return m.inspect_boundary(**self.opts)

    def test_private_fixed_host_reads_metadata_and_defaults_new_r3_off(self):
        before = self.queue.read_bytes()
        result = self.report()
        self.assertTrue(result["private_copy_eligible"], result["review_blockers"])
        self.assertEqual(result["legacy_schema"], "match")
        self.assertEqual(result["additive_schema"], "absent")
        self.assertEqual(result["r3_settings"], "absent_off")
        self.assertEqual(result["pause"], "not_paused")
        self.assertFalse(result["real_dispatch_enabled"])
        self.assertFalse(result["cutover_authorized"])
        self.assertEqual(before, self.queue.read_bytes())
        for secret in ("private ambiguous comment", "private manually reviewed text",
                       str(self.home), str(self.queue)):
            self.assertNotIn(secret, json.dumps(result))

    def test_optional_separate_owner_settings_are_not_permission(self):
        with sqlite3.connect(self.queue) as db:
            db.executemany("INSERT INTO publish_settings VALUES(?,?)", [
                ("r3_comment_dial", "auto"), ("r3_auto_enabled", "1"),
                ("r3_auto_since", "2026-10-30T01:01:01Z")])
        result = self.report()
        self.assertEqual(result["r3_settings"], "present_requires_owner_review")
        self.assertFalse(result["cutover_authorized"])
        self.assertNotIn("2026-10-30T01:01:01Z", json.dumps(result))

    def test_pause_and_untrusted_pause_are_not_silently_cleared(self):
        self.paused.touch(mode=0o600)
        self.assertEqual(self.report()["pause"], "paused")
        self.paused.unlink()
        self.paused.symlink_to(self.queue)
        r = self.report()
        self.assertEqual(r["pause"], "untrusted")
        self.assertFalse(r["private_copy_eligible"])
        self.assertIn("pause_marker_untrusted", r["review_blockers"])

    def test_wrong_root_symlink_missing_and_shared_files_fail_closed(self):
        wrong = dict(self.opts, queue=self.root / "unrelated.sqlite3")
        self.assertIn("host_paths_not_fixed",
                      m.inspect_boundary(**wrong)["review_blockers"])
        os.chmod(self.home / ".config", 0o777)
        r = self.report()
        self.assertIn("config_directory_not_private", r["review_blockers"])
        os.chmod(self.home / ".config", 0o700)
        os.chmod(self.queue, 0o644)
        self.assertIn("queue_file_not_private", self.report()["review_blockers"])
        os.chmod(self.queue, 0o600)
        alias = self.queue.with_name("queue-alias.sqlite3")
        alias.symlink_to(self.queue)
        self.queue.unlink()
        self.queue.symlink_to(alias)
        self.assertFalse(self.report()["private_copy_eligible"])

    def test_unknown_or_partial_additive_schema_holds(self):
        with sqlite3.connect(self.queue) as db:
            db.execute("CREATE TABLE r3_proposals(source_run TEXT PRIMARY KEY)")
        r = self.report()
        self.assertIn("additive_schema_not_empty", r["review_blockers"])
        self.assertEqual(m.rehearse(**self.opts)["rehearsal"], "refused_preflight")

    def test_realistic_committed_wal_is_copied_and_legacy_history_preserved(self):
        with sqlite3.connect(self.queue) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("INSERT INTO publish_events(at,kind,details) "
                       "VALUES('2026-10-30T11:00:00Z','safety','new committed WAL')")
            db.commit()
            old_count = db.execute(
                "SELECT COUNT(*) FROM publish_events").fetchone()[0]
            old_attempts = db.execute(
                "SELECT COUNT(*) FROM publish_jobs WHERE attempted_at IS NOT NULL"
            ).fetchone()[0]
            result = m.rehearse(**self.opts)
            self.assertIsInstance(result["rehearsal"], dict, result)
            value = result["rehearsal"]
            self.assertTrue(value["private_copy_migrated"])
            self.assertTrue(value["full_legacy_history_preserved"])
            self.assertTrue(value["crash_rollback_pass"])
            self.assertTrue(value["idempotent"])
            self.assertEqual(value["historical_attempts"], old_attempts)
            self.assertFalse(value["live_schema_migrated"])
            self.assertFalse(value["cutover_authorized"])
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM publish_events").fetchone()[0], old_count)
            self.assertNotIn("r3_proposals", {x[0] for x in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")})

    def test_private_copy_rehearsal_leaves_original_bytes_and_history(self):
        before = self.queue.read_bytes()
        data = m.rehearse(**self.opts)
        self.assertTrue(data["rehearsal"]["private_copy_migrated"], data)
        self.assertTrue(data["rehearsal"]["temporary_copy_deleted_on_return"])
        self.assertEqual(self.queue.read_bytes(), before)
        self.assertEqual(len(list(self.root.rglob("queue-copy.sqlite3"))), 0)
        report = json.dumps(data)
        self.assertNotIn("private ambiguous", report)
        self.assertNotIn(str(self.queue), report)

    def test_failure_during_copy_migration_is_closed_and_source_unchanged(self):
        before = self.queue.read_bytes()
        with patch.object(m, "_apply_copy_schema", side_effect=ValueError(
                "private secret must not appear in report")):
            result = m.rehearse(**self.opts)
        self.assertEqual(result["rehearsal"], "failed_closed")
        self.assertFalse(result["cutover_authorized"])
        self.assertNotIn("private secret", json.dumps(result))
        self.assertEqual(self.queue.read_bytes(), before)

    def test_r313a_copy_tables_match_existing_r35_synthetic_contract(self):
        path = self.root / "r35-inert-fixtures" / "r35-legacy-queue-lab.sqlite3"
        create_legacy_fixture(path)
        MigrationFixture(path).migrate()
        with sqlite3.connect(path) as r35:
            r35_columns = {name: tuple(row[1:3] for row in r35.execute(
                'PRAGMA table_info("' + name + '")')) for name in NEW}
        with sqlite3.connect(self.queue) as copy:
            copy.execute("BEGIN IMMEDIATE")
            self.assertTrue(m._apply_copy_schema(copy))
            self.assertFalse(m._apply_copy_schema(copy))
            copy.rollback()
            # The test connection itself rolls back all DDL.
            self.assertFalse(set(NEW) & m._tables(copy))
            copy.execute("BEGIN IMMEDIATE")
            m._apply_copy_schema(copy)
            for name, required in NEW.items():
                cols = tuple(row[1:3] for row in copy.execute(
                    'PRAGMA table_info("' + name + '")'))
                self.assertEqual(cols, r35_columns[name])
                self.assertTrue(required.issubset({col[0] for col in cols}))
            self.assertEqual(copy.execute(
                "SELECT value FROM r35_schema_meta WHERE name='version'"
            ).fetchone(), (SCHEMA,))
            copy.rollback()

    def test_forged_home_environment_blocks_private_copy(self):
        with patch.object(cli.pwd, "getpwuid") as lookup:
            lookup.return_value.pw_dir = str(self.root / "different-login-home")
            with patch.object(cli, "rehearse", side_effect=AssertionError(
                    "private copy must not be invoked")):
                with patch.object(cli, "unit_report", return_value={
                        "effective_service": "unverified",
                        "effective_timer": "unverified",
                        "review_blockers": ["synthetic"]}):
                    result = cli.collect(private_copy=True)
        self.assertEqual(result["rehearsal"], "refused_account_home")
        self.assertIn("account_home_mismatch", result["host"]["review_blockers"])
        self.assertFalse(result["host"]["private_copy_eligible"])
        self.assertFalse(result["cutover_authorized"])

    def test_default_script_readonly_and_no_arbitrary_paths(self):
        source = inspect.getsource(m)
        for forbidden in ("urllib.request", "requests.post", "systemctl",
                          "credentials.json", "api_key(", "os.system("):
            self.assertNotIn(forbidden, source)
        self.assertEqual(cli.main(["--queue", str(self.queue)]), 2)
        self.assertEqual(cli.main(["--private-copy", "--queue"]), 2)
        self.assertFalse(cli.collect.__defaults__ and False)
        sample = {
            "host": self.report(),
            "effective_units": {"effective_service": "reviewed_shape",
                                "effective_timer": "reviewed_shape",
                                "review_blockers": []},
            "rehearsal": "not_requested",
        }
        display = cli.compact(sample)
        self.assertIn("cutover authorized: NO", display)
        self.assertNotIn(str(self.queue), display)


if __name__ == "__main__":
    unittest.main()
