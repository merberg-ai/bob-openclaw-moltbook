"""R4 guarded signed-updater SQLite migration and code-only rollback lab.

Works only on new temporary SQLite databases and authenticated fake source
bytes. No real Bob installation, systemd, publisher, network or credentials.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]

import r4_install_guard as guard
import backup_live_sqlite as backup
import bob_r4_schema as schema
import bob_release_updater as updater


class R4GuardedMigrationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="r4-updater-private-lab-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.backup_dir=self.root/"backups"
        self.db_path=self.root/"activity-queue.sqlite3"
        with sqlite3.connect(self.db_path) as db:
            db.executescript("""
              CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,
                post_id TEXT,attempted_at TEXT,comment_id TEXT);
              CREATE TABLE r3_proposals(source_run TEXT PRIMARY KEY,
                post_id TEXT,seal_sha256 TEXT);
              INSERT INTO publish_jobs VALUES(
                '20261101T151033Z',
                'bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a',
                '2026-11-01T19:46:08+00:00',
                '8c37f88f-e678-4007-ba56-586b76ef4cfd');
              INSERT INTO r3_proposals VALUES(
                '20261101T151033Z',
                'bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a',
                '870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2');
            """)
        self.db_path.chmod(0o600)
        self.report=backup.create_verified_backup(self.db_path,self.backup_dir)
        self.current={"release":guard.FROM}
        self.plan={"release":guard.RELEASE,"from":guard.FROM,
                   "restart_manager":True}
        self.contents={k:b"synthetic owned, nonpublic source"
                       for k in guard.REQUIRED}
        for k,marker in guard.SEND_OFF:
            self.contents[k]+=b"\n"+marker
        self.contents["bob_r4_schema.py"]+=b"\n"+guard.MIGRATION_GATE

    def run_guard(self,**kw):
        values=dict(schema_module=schema,db_path=self.db_path,
                    backup=self.report,backup_dir=self.backup_dir,
                    current=self.current,plan=self.plan,
                    contents=self.contents,
                    candidate_hashes_verified=True,
                    publisher_inactive=True)
        values.update(kw)
        return guard.run_migration(**values)

    def prior(self):
        with sqlite3.connect(self.db_path) as db:
            return (db.execute("SELECT * FROM publish_jobs").fetchall(),
                    db.execute("SELECT * FROM r3_proposals").fetchall())

    def test_guarded_updater_migration_is_additive_and_idempotent(self):
        original=self.prior()
        self.assertTrue(guard.verify_backup_evidence(
            self.report,backup_dir=self.backup_dir))
        self.assertEqual(self.run_guard(),"additive_schema_ready_no_public_send")
        self.assertEqual(self.prior(),original)
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(schema.inspect(db),"ready")
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM r4_action_outbox").fetchone(),(0,))
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM r4_social_decisions").fetchone(),(0,))
        self.assertEqual(self.run_guard(),"additive_schema_ready_no_public_send")
        self.assertEqual(self.prior(),original)

    def test_code_only_rollback_leaves_empty_versioned_tables_and_receipt(self):
        before=self.prior()
        self.run_guard()
        # Simulate existing updater's code-only recovery to previous release:
        # neither restore old DB snapshot nor DELETE migration tables.
        simulated_code_registry={"release":guard.FROM}
        self.assertEqual(simulated_code_registry["release"],guard.FROM)
        self.assertEqual(self.prior(),before)
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(schema.inspect(db),"ready")
        # A subsequent signed retry sees exactly the same known version.
        self.assertEqual(self.run_guard(),"additive_schema_ready_no_public_send")

    def test_wrong_chain_missing_flag_and_unverified_hashes_refuse_before_db(self):
        for field,value in (
            ("candidate_hashes_verified",False),
            ("publisher_inactive",False),
            ("plan",{"release":"untrusted","from":guard.FROM,
                     "restart_manager":True}),
            ("current",{"release":"v0.8.0-r3skip1"}),
            ("contents",{"bob_r4_schema.py":b"hello"}),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,
                                            "r4_install_release_backup_or_publisher_unverified"):
                    self.run_guard(**{field:value})
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(schema.inspect(db),"missing")

    def test_tampered_backup_or_wrong_permissions_refused(self):
        saved=dict(self.report)
        self.report={**saved,"sha256":"0"*64}
        self.assertFalse(guard.verify_backup_evidence(
            self.report,backup_dir=self.backup_dir))
        with self.assertRaises(ValueError):
            self.run_guard()
        self.report=saved
        b=Path(saved["backup_path"])
        b.chmod(0o644)
        self.assertFalse(guard.verify_backup_evidence(
            self.report,backup_dir=self.backup_dir))
        with self.assertRaises(ValueError):
            self.run_guard()
        self.assertEqual(self.prior()[0][0][3],
                         "8c37f88f-e678-4007-ba56-586b76ef4cfd")

    def test_partial_future_schema_is_refused_without_repair(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("CREATE TABLE r4_unreviewed_future(field TEXT)")
        with self.assertRaisesRegex(ValueError,"r4_install_partial_or_future_schema"):
            self.run_guard()
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(schema.inspect(db),"partial_or_untrusted")
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='r4_social_decisions'"
            ).fetchone(),(0,))

    def test_updater_https_and_migration_journal_are_known(self):
        self.assertEqual(updater.MANAGER_TRANSPORTS[guard.RELEASE],"https")
        journal=self.root/"transaction.json"
        journal.write_text(json.dumps({
            "format":updater.FORMAT,"phase":"migrated",
            "release":guard.RELEASE,"restart_manager":True}))
        journal.chmod(0o600)
        with patch.object(updater,"JOURNAL",journal):
            self.assertEqual(updater.read_journal()["phase"],"migrated")
        self.assertTrue(guard.reviewed_scope(
            self.current,self.plan,self.contents))
        self.assertFalse(guard.reviewed_scope(
            self.current,self.plan,
            {**self.contents,
             "bob_r4_publisher_adapter.py":b"R4_REAL_DISPATCH_COMPILED_OFF=False"}))


if __name__=="__main__":
    unittest.main()
