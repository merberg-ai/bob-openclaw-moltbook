"""R3.5 offline migration and reboot regression, on disposable private SQLite only."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import os
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bob_v08.r35_migration_lab import (
    MigrationFixture, MARKER, SCHEMA, reboot_reconcile,
)
from bob_v08.r3_cutover_rehearsal import CutoverState, rehearse_cutover


def create_legacy_fixture(path: Path, *, marker=MARKER):
    path.parent.mkdir(mode=0o700)
    with sqlite3.connect(path) as db:
        # These legacy tables follow src/lib/bob/bob_publish_common.py:connect.
        db.executescript("""
        CREATE TABLE decisions (
            run_id TEXT PRIMARY KEY, draft_sha256 TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('approved','rejected')),
            decided_at TEXT NOT NULL
        );
        CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE publish_jobs (
            run_id TEXT PRIMARY KEY, approval_sha256 TEXT NOT NULL,
            post_id TEXT NOT NULL,draft_comment TEXT NOT NULL,
            mode TEXT NOT NULL CHECK(mode IN ('manual','auto')),
            state TEXT NOT NULL,created_at TEXT NOT NULL,attempted_at TEXT,
            comment_id TEXT,challenge_code TEXT,challenge_text TEXT,
            challenge_expires_at TEXT,verify_answer TEXT,last_error TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE published_replies(
            id TEXT PRIMARY KEY,post_id TEXT NOT NULL,comment_id TEXT NOT NULL,
            author TEXT,content TEXT,detected_at TEXT NOT NULL);
        CREATE TABLE publish_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,
            kind TEXT NOT NULL,details TEXT NOT NULL);
        CREATE TABLE r35_fixture_meta(
            name TEXT PRIMARY KEY,value TEXT NOT NULL);
        """)
        db.execute("INSERT INTO r35_fixture_meta VALUES('contract',?)", (marker,))
        db.executemany("INSERT INTO publish_settings VALUES(?,?)", [
            ("auto_enabled","0"), ("activity_limit_comment_daily","2"),
            ("activity_limit_comment_auto_daily","1")])
        db.execute("INSERT INTO decisions VALUES(?,?,?,?)", (
            "20261030T230000Z","a"*64,"approved","2026-10-30T23:10:00Z"))
        db.executemany("""INSERT INTO publish_jobs
            (run_id,approval_sha256,post_id,draft_comment,mode,state,
             created_at,attempted_at,comment_id,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", [
            ("20261030T230000Z","a"*64,"11111111-1111-4111-8111-111111111111",
             "private manually reviewed text","manual","queued",
             "2026-10-30T23:10:00Z",None,None,"2026-10-30T23:10:00Z"),
            ("20261030T220000Z","b"*64,"22222222-2222-4222-8222-222222222222",
             "private ambiguous comment text","auto","uncertain",
             "2026-10-30T22:00:00Z","2026-10-30T22:01:00Z",None,
             "2026-10-30T22:01:00Z"),
        ])
        db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",(
            "2026-10-30T22:01:00Z","publish_uncertain","historical event"))
        db.execute("INSERT INTO published_replies VALUES(?,?,?,?,?,?)", (
            "reply-1","22222222-2222-4222-8222-222222222222",
            "comment-1","Other","sample history","2026-10-30T22:10:00Z"))
    os.chmod(path, 0o600)


class AdditiveMigrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.file = self.root / "r35-inert-fixtures" / "r35-legacy-queue-lab.sqlite3"
        create_legacy_fixture(self.file)
        self.lab = MigrationFixture(self.file)

    def test_additive_migration_preserves_every_legacy_record_and_repeats(self):
        before = self.lab.history_summary()
        with sqlite3.connect(self.file) as db:
            old = {name: db.execute(f"SELECT * FROM {name} ORDER BY 1").fetchall()
                   for name in ("publish_jobs", "decisions", "publish_settings",
                                "publish_events", "published_replies")}
        one = self.lab.migrate()
        two = self.lab.migrate()
        self.assertTrue(one.migrated)
        self.assertEqual(one.schema_version, SCHEMA)
        self.assertEqual((one.existing_attempts, one.existing_uncertain), (1,1))
        self.assertTrue(one.preserved_legacy_rows)
        self.assertEqual(one, two)
        self.assertEqual(before, self.lab.history_summary())
        with sqlite3.connect(self.file) as db:
            for name, rows in old.items():
                self.assertEqual(db.execute(f"SELECT * FROM {name} ORDER BY 1").fetchall(),
                                 rows)
            self.assertEqual(db.execute(
                "SELECT value FROM r35_schema_meta WHERE name='version'").fetchone(),
                (SCHEMA,))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM r3_proposals").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM r3_owner_approvals").fetchone()[0],0)

    def test_injected_power_loss_during_ddl_rolls_back_all_new_tables(self):
        before = self.lab.history_summary()
        with self.assertRaisesRegex(RuntimeError,"synthetic_power_loss"):
            self.lab.migrate(inject_crash=True)
        with sqlite3.connect(self.file) as db:
            names={r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("r3_proposals",names)
            self.assertNotIn("r35_schema_meta",names)
        self.assertEqual(before, self.lab.history_summary())
        self.assertTrue(self.lab.migrate().migrated)

    def test_wrong_existing_proposal_schema_is_not_overwritten(self):
        with sqlite3.connect(self.file) as db:
            db.execute("CREATE TABLE r3_proposals (source_run TEXT PRIMARY KEY)")
        with self.assertRaisesRegex(ValueError,"r35_additive_schema_drift"):
            self.lab.migrate()
        with sqlite3.connect(self.file) as db:
            self.assertNotIn("r35_schema_meta", {r[0] for r in
                db.execute("SELECT name FROM sqlite_master WHERE type='table'")})
            self.assertEqual(db.execute("PRAGMA table_info(r3_proposals)").fetchall()[1:],
                             [])

    def test_unknown_schema_version_denies_without_reverting(self):
        self.lab.migrate()
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE r35_schema_meta SET value='future-unknown'")
        before=self.lab.history_summary()
        with self.assertRaisesRegex(ValueError,"unknown_r35_schema"):
            self.lab.migrate()
        self.assertEqual(before,self.lab.history_summary())

    def test_code_rollback_never_rewinds_more_recent_attempts(self):
        self.lab.migrate()
        # Simulate new history being written after upgrade, before code rollback.
        with sqlite3.connect(self.file) as db:
            db.execute("""INSERT INTO publish_jobs (
                run_id,approval_sha256,post_id,draft_comment,mode,state,
                created_at,attempted_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                ("20261030T235000Z","c"*64,"33333333-3333-4333-8333-333333333333",
                 "new attempted reply","auto","uncertain","2026-10-30T23:50:00Z",
                 "2026-10-30T23:51:00Z","2026-10-30T23:51:00Z"))
        counts, digest = self.lab.history_summary()
        self.assertEqual(counts,(2,2))
        start=CutoverState(attempted=("old-1","new-2"),
                           uncertain=("old-1","new-2"))
        staged=rehearse_cutover(start,"stage").state
        quiesced=rehearse_cutover(staged,"quiesce",legacy_drained=True,
            backup_verified=True,rollback_rehearsed=True).state
        # Simulated rollback changes only code/timer ownership, not SQLite data.
        back=rehearse_cutover(quiesced,"rollback")
        self.assertTrue(back.accepted)
        self.assertEqual(back.state.attempted,start.attempted)
        self.assertEqual(back.state.uncertain,start.uncertain)
        self.assertEqual(self.lab.history_summary(),(counts,digest))
        with sqlite3.connect(self.file) as db:
            self.assertEqual(db.execute(
                "SELECT state FROM publish_jobs WHERE run_id='20261030T235000Z'"
            ).fetchone(),("uncertain",))
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM publish_jobs WHERE state='queued'"
            ).fetchone()[0],1)

    def test_unmarked_symlink_nonprivate_and_wrong_path_refused(self):
        wrong=self.root/"activity-queue.sqlite3"
        with self.assertRaisesRegex(ValueError,"not_an_r35_fixture"):
            MigrationFixture(wrong).migrate()
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE r35_fixture_meta SET value='imposter'")
        with self.assertRaisesRegex(ValueError,"invalid_r35_marker"):
            self.lab.migrate()
        linkdir=self.root/"subdir"
        linkdir.mkdir(mode=0o700)
        link=linkdir/"r35-inert-fixtures"
        link.symlink_to(self.file.parent,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,"unsafe_r35_fixture"):
            MigrationFixture(link/self.file.name).migrate()
        os.chmod(self.file,0o644)
        with self.assertRaisesRegex(ValueError,"nonprivate_r35_fixture"):
            self.lab.migrate()

    def test_legacy_schema_drift_refuses_before_migration(self):
        with sqlite3.connect(self.file) as db:
            db.execute("DROP TABLE publish_jobs")
            db.execute("CREATE TABLE publish_jobs (run_id TEXT)")
        with self.assertRaisesRegex(ValueError,"legacy_queue_schema_drift"):
            self.lab.migrate()


class RebootOwnershipTests(unittest.TestCase):
    def test_baseline_restart_known_legacy_only(self):
        result=reboot_reconcile(CutoverState(),legacy_timer=True,
            candidate_timer=False,legacy_worker=False,candidate_worker=False,
            startup_reconcile_verified=True)
        self.assertTrue(result.safe_to_resume)
        self.assertEqual(result.verdict,"legacy_only_after_boot")
        self.assertFalse(result.changed_host)

    def test_overlap_and_split_controllers_fail_closed(self):
        for state in (
            dict(legacy_timer=True,candidate_timer=True,
                 legacy_worker=False,candidate_worker=False),
            dict(legacy_timer=False,candidate_timer=False,
                 legacy_worker=True,candidate_worker=True),
            dict(legacy_timer=True,candidate_timer=False,
                 legacy_worker=False,candidate_worker=True),
        ):
            with self.subTest(**state):
                r=reboot_reconcile(CutoverState(),**state,
                                   startup_reconcile_verified=True)
                self.assertFalse(r.safe_to_resume)
                self.assertIn(r.verdict,(
                    "overlapping_publisher_ownership","split_publisher_ownership"))
                self.assertFalse(r.changed_host)

    def test_candidate_after_reboot_requires_fresh_human_review(self):
        r=reboot_reconcile(CutoverState(phase="candidate",
            legacy_publisher_timer=False,candidate_publisher_timer=True),
            legacy_timer=False,candidate_timer=True,
            legacy_worker=False,candidate_worker=False,
            startup_reconcile_verified=True)
        self.assertEqual(r.verdict,"candidate_requires_fresh_owner_review")
        self.assertFalse(r.safe_to_resume)

    def test_undrainable_or_unknown_reconcile_holds(self):
        r=reboot_reconcile(CutoverState(),
            legacy_timer=True,candidate_timer=False,
            legacy_worker=False,candidate_worker=False,
            startup_reconcile_verified=False)
        self.assertEqual(r.verdict,"startup_reconcile_unverified")
        self.assertFalse(r.safe_to_resume)
        bad=reboot_reconcile(CutoverState(),
            legacy_timer=True,candidate_timer=False,
            legacy_worker=False,candidate_worker=False,
            startup_reconcile_verified="yes")
        self.assertEqual(bad.verdict,"invalid_restart_snapshot")

    def test_quiesced_boot_does_not_turn_either_timer_on(self):
        state=CutoverState(phase="quiesced",legacy_publisher_timer=False)
        r=reboot_reconcile(state,legacy_timer=False,candidate_timer=False,
                           legacy_worker=False,candidate_worker=False,
                           startup_reconcile_verified=True)
        self.assertEqual(r.verdict,"quiesced_requires_manual_recovery")
        self.assertFalse(r.safe_to_resume)
        self.assertFalse(r.changed_host)


class DeploymentReportTests(unittest.TestCase):
    def test_inert_cli_report_denies_production_authority(self):
        sys.path.insert(0,str(ROOT/"scripts"))
        from rehearse_r35_deployment import report
        outcome=report()
        self.assertTrue(outcome["legacy_schema_additive"])
        self.assertTrue(outcome["legacy_history_preserved"])
        self.assertTrue(outcome["migration_idempotent"])
        self.assertTrue(outcome["crash_before_commit_rolled_back"])
        self.assertEqual(outcome["inert_service_templates_checked"],4)
        self.assertTrue(outcome["unapproved_cutover_denied"])
        self.assertTrue(outcome["unverified_reboot_kept_paused"])
        self.assertTrue(outcome["rollback_preserves_unknowns"])
        self.assertFalse(outcome["cutover_authorized"])
        self.assertEqual(outcome["external_requests"],0)
        self.assertEqual(outcome["live_unit_changes"],0)

    def test_altered_inert_publisher_timer_is_rejected(self):
        sys.path.insert(0,str(ROOT/"scripts"))
        import rehearse_r35_deployment as app
        with tempfile.TemporaryDirectory() as root:
            original=app.write_timer
            def tampered(role):
                value=original(role)
                return (value.replace("Unit="+app.PREFIX+"publisher.service",
                                      "Unit=bad-publisher.service")
                        if role == "publisher" else value)
            with patch.object(app,"write_timer",side_effect=tampered):
                self.assertFalse(app.inert_template_gate(Path(root)))


if __name__ == "__main__":
    unittest.main()
