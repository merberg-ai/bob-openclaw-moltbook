"""R4 production-shaped transaction rehearsal using the REAL candidate payload.

Only a disposable, file-backed private SQLite database and temporary installed
binary/registry/journal trees. The actual signed updater's update(), backup,
hash gate, versioned migration and rollback() execute. Systemd and HTTPS
health are controlled at the boundary; no sockets, credentials, or real
Moltbook calls exist in this harness. Never point this at an operator home.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src/lib/bob")]

import bob_release_updater as updater
import bob_r4_schema as schema

OLD_RELEASE = "v0.8.0-r3canary1"
R4_RELEASE = "v0.8.0-autonomy1"
CANARY_RUN = "20261101T151033Z"
CANARY_ID = "8c37f88f-e678-4007-ba56-586b76ef4cfd"


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


class R4ProductionShapeRehearsal(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="r4-transaction-isolated-")
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.bin = self.home / ".local/bin"
        self.state = self.home / ".local/state/bob-updater"
        self.dbpath = self.home / ".config/moltbook/activity-queue.sqlite3"
        self.backups = self.home / ".local/state/bob-baseline/backups"
        for directory in (self.bin, self.state, self.dbpath.parent):
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        with sqlite3.connect(self.dbpath) as db:
            db.executescript("""
                CREATE TABLE publish_jobs (
                  run_id TEXT PRIMARY KEY,
                  post_id TEXT,
                  attempted_at TEXT,
                  comment_id TEXT
                );
                INSERT INTO publish_jobs VALUES (
                  '20261101T151033Z',
                  'bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a',
                  '2026-11-01T19:46:08+00:00',
                  '8c37f88f-e678-4007-ba56-586b76ef4cfd'
                );
                CREATE TABLE r3_proposals (
                  source_run TEXT PRIMARY KEY,
                  post_id TEXT,
                  seal_sha256 TEXT
                );
                INSERT INTO r3_proposals VALUES (
                  '20261101T151033Z',
                  'bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a',
                  '870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2'
                );
            """)
        self.dbpath.chmod(0o600)
        self.old_bytes = b"#!/usr/bin/env python3\n# Synthetic previous bobctl\n"
        (self.bin / "bobctl").write_bytes(self.old_bytes)
        (self.bin / "bobctl").chmod(0o700)
        self.current = {
            "format": updater.FORMAT,
            "release": OLD_RELEASE,
            "files": {"bobctl": digest(self.old_bytes)},
        }
        self.registry = self.state / "installed.json"
        self.registry.write_text(json.dumps(self.current))
        self.registry.chmod(0o600)
        self.journal = self.state / "transaction.json"
        planfile = ROOT / "releases/candidates/r4-autonomy1-consolidated.json"
        self.plan = json.loads(planfile.read_text(encoding="utf-8"))
        self.assertEqual(self.plan["from"], OLD_RELEASE)
        self.assertEqual(self.plan["release"], R4_RELEASE)
        # This is the complete actual source/builder manifest, not stand-in
        # strings for the migration or R4 dependencies.
        self.contents = {
            item["name"]: updater.release_bytes(ROOT, item)
            for item in self.plan["files"]
        }

    @contextmanager
    def isolated_host(self):
        """Patch only host paths and external service/HTTPS boundaries."""
        with ExitStack() as stack:
            for attribute, path in (
                ("BIN", self.bin),
                ("STATE_DIR", self.state),
                ("LOCK", self.state / "lock"),
                ("REGISTRY", self.registry),
                ("JOURNAL", self.journal),
                ("DB", self.dbpath),
                ("BACKUP_DIR", self.backups),
            ):
                stack.enter_context(patch.object(updater, attribute, path))
            stack.enter_context(patch.object(
                updater, "r4_publisher_inactive", return_value=True))
            stack.enter_context(patch.object(
                updater, "healthy", return_value=True))
            health = stack.enter_context(patch.object(
                updater, "wait_for_health", return_value=True))
            restart = stack.enter_context(patch.object(
                updater, "restart_manager"))
            yield health, restart

    def rows(self, table: str):
        # Fixed test-controlled table identifiers, never external input.
        self.assertIn(table, ("publish_jobs", "r3_proposals"))
        with sqlite3.connect(self.dbpath) as db:
            return db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()

    def test_real_payload_backup_migration_registry_and_no_public_send(self):
        before = (self.rows("publish_jobs"), self.rows("r3_proposals"))
        with self.isolated_host() as (health, restart):
            self.assertEqual(
                updater.update(ROOT, self.current, self.plan, self.contents,
                               auth="Basic isolated-test"), "updated")
            installed = updater.registry()
            self.assertEqual(installed["release"], R4_RELEASE)
            self.assertTrue(updater.live_ok(installed))
            self.assertEqual(updater.read_journal()["phase"], "complete")
            self.assertEqual(updater.manager_transport(R4_RELEASE), "https")
            restart.assert_called_once()
            self.assertEqual(health.call_args.kwargs["release"], R4_RELEASE)
            for name in self.contents:
                self.assertEqual((self.bin / name).read_bytes(),
                                 self.contents[name])
            self.assertTrue(any(self.backups.glob("bob-activity-*.sqlite3")))
        self.assertEqual(before, (self.rows("publish_jobs"),
                                  self.rows("r3_proposals")))
        with sqlite3.connect(self.dbpath) as db:
            self.assertEqual(schema.inspect(db), "ready")
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM r4_action_outbox"
            ).fetchone()[0], 0)
        self.assertEqual(
            (self.bin / "bob_r4_publisher_adapter.py").read_bytes().count(
                b"R4_REAL_DISPATCH_COMPILED_OFF=True"), 1)

    def test_failed_candidate_https_postflight_restores_code_not_database(self):
        before = self.rows("publish_jobs")
        with self.isolated_host() as (health, restart):
            health.side_effect = (
                lambda auth, release=None: release == OLD_RELEASE)
            self.assertEqual(
                updater.update(ROOT, self.current, self.plan, self.contents,
                               auth="Basic isolated-test"), "rolled_back")
            self.assertEqual(updater.read_journal()["phase"], "rolled_back")
            self.assertEqual(updater.registry()["release"], OLD_RELEASE)
            self.assertTrue(updater.live_ok(self.current))
            self.assertEqual(restart.call_count, 2)
            for name in self.contents:
                if name != "bobctl":
                    self.assertFalse((self.bin / name).exists(), name)
        self.assertEqual(self.rows("publish_jobs"), before)
        with sqlite3.connect(self.dbpath) as db:
            self.assertEqual(schema.inspect(db), "ready")

    def test_interrupted_migrated_phase_recovery_keeps_new_attempt_records(self):
        with self.isolated_host() as (_, restart):
            calls = []
            def interrupt_once():
                calls.append("restart")
                if len(calls) == 1:
                    raise KeyboardInterrupt("synthetic process interruption")
            restart.side_effect = interrupt_once
            with self.assertRaises(KeyboardInterrupt):
                updater.update(ROOT, self.current, self.plan, self.contents,
                               auth="Basic isolated-test")
            self.assertEqual(updater.read_journal()["phase"], "migrated")
            self.assertEqual(updater.registry()["release"], R4_RELEASE)
            with sqlite3.connect(self.dbpath) as db:
                self.assertEqual(schema.inspect(db), "ready")
                # Simulate a concurrently durable attempted publication after
                # migration: recovery must NOT restore an older DB snapshot.
                db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?)", (
                    "20261101T200000Z", "later-post",
                    "2026-11-01T20:00:00+00:00", "later-comment"))
            restart.side_effect = None
            self.assertEqual(
                updater.rollback(updater.read_journal(),
                                 auth="Basic isolated-test"),
                "baseline_restored")
            self.assertEqual(updater.read_journal()["phase"], "rolled_back")
            self.assertEqual(updater.registry()["release"], OLD_RELEASE)
            self.assertTrue(updater.live_ok(self.current))
        rows = self.rows("publish_jobs")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][3], CANARY_ID)
        self.assertEqual(rows[1][0], "20261101T200000Z")
        with sqlite3.connect(self.dbpath) as db:
            self.assertEqual(schema.inspect(db), "ready")


if __name__ == "__main__":
    unittest.main()
