"""Versioned R4 additive schema rehearsal; zero production migrations."""
import sqlite3
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_schema as schema


class R4SchemaTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,
            attempted_at TEXT,post_id TEXT,comment_id TEXT);
          CREATE TABLE r3_proposals(source_run TEXT PRIMARY KEY,
            seal_sha256 TEXT);
          INSERT INTO publish_jobs VALUES(
            '20261101T151033Z','2026-11-01T19:46:08+00:00',
            'bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a',
            '8c37f88f-e678-4007-ba56-586b76ef4cfd');
          INSERT INTO r3_proposals VALUES(
            '20261101T151033Z',
            '870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2');
        """)

    def test_migration_requires_explicit_signed_updater_guard_flags(self):
        # Source schema primitive is now staged for the eventual signed
        # updater. The updater itself must independently prove backup, host,
        # installed hashes and publisher inactivity before calling it.
        self.assertFalse(schema.INSTALL_HOOK_COMPILED_OFF)
        self.assertEqual(schema.inspect(self.db),"missing")
        for kwargs in (
            {"trusted_owner":False,"backup_verified":True,
             "installed_release":schema.RELEASE},
            {"trusted_owner":True,"backup_verified":False,
             "installed_release":schema.RELEASE},
            {"trusted_owner":True,"backup_verified":True,
             "installed_release":"v0.8.0-r3canary1"},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError,
                                            "r4_migration_not_authorized_for_install"):
                    schema.migrate_candidate(self.db,**kwargs)
        self.assertEqual(schema.inspect(self.db),"missing")

    def test_offline_rehearsal_additive_idempotent_and_preserves_canary(self):
        before=self.db.execute(
            "SELECT * FROM publish_jobs").fetchall()
        r3=self.db.execute(
            "SELECT * FROM r3_proposals").fetchall()
        self.assertEqual(schema.rehearsal(self.db),"ready")
        self.assertEqual(schema.rehearsal(self.db),"ready")
        self.assertEqual(schema.inspect(self.db),"ready")
        self.assertEqual(self.db.execute(
            "SELECT * FROM publish_jobs").fetchall(),before)
        self.assertEqual(self.db.execute(
            "SELECT * FROM r3_proposals").fetchall(),r3)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_evidence_suggestions").fetchone(),(0,))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_social_decisions").fetchone(),(0,))

    def test_partial_unknown_or_future_schema_refuses_without_repair(self):
        self.db.execute("CREATE TABLE r4_social_decisions(source_run TEXT)")
        self.assertEqual(schema.inspect(self.db),"partial_or_untrusted")
        with self.assertRaisesRegex(ValueError,
                                    "r4_existing_partial_schema_refused"):
            schema.rehearsal(self.db)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
            "AND name='r4_evidence_suggestions'").fetchone(),(0,))
        self.db.execute("DROP TABLE r4_social_decisions")
        self.db.execute("CREATE TABLE r4_unknown_future(status TEXT)")
        self.assertEqual(schema.inspect(self.db),"partial_or_untrusted")
        with self.assertRaises(ValueError):
            schema.rehearsal(self.db)

    def test_version_drift_is_rejected_without_touching_existing_rows(self):
        schema.rehearsal(self.db)
        self.db.execute("UPDATE r4_schema_meta SET value='unknown'")
        self.assertEqual(schema.inspect(self.db),"partial_or_untrusted")
        with self.assertRaises(ValueError):
            schema.rehearsal(self.db)
        self.assertEqual(self.db.execute(
            "SELECT attempted_at FROM publish_jobs").fetchone(),
            ("2026-11-01T19:46:08+00:00",))

    def test_read_only_inspection_creates_nothing(self):
        before=self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        for _ in range(3):
            self.assertEqual(schema.inspect(self.db),"missing")
        after=self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        self.assertEqual(before,after)


if __name__=="__main__":
    unittest.main()
