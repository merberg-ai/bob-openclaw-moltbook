"""R3.13d staging gate: no installed writes, all migration work on private copies.

This is NOT a live cutover test. The source-only owner controls remain Off.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"),str(ROOT/"src"/"lib"/"bob"),
                str(ROOT/"scripts"),str(ROOT/"tests")]

from bob_v08.core import Action
from bob_v08.r313a_private_migration import _history_counts, _history_digest, _tables
from bob_v08.r313b_upgrade_contract import (
    LAB_DIR, LAB_FILE, LAB_MARKER, LAB_MARKER_VALUE,
    OFF_SETTINGS, upgrade_private_copy, review_permission,
)
from bob_v08.r313c_candidate import _read_envelope
from bob_v08.r313d_staging import (
    _schema_shape, _off, migrate_marked_copy,
    propose_on_marked_copy, source_off_gate,
)
from test_r35_migration_recovery import create_legacy_fixture
from test_r3_cutover_rehearsal import make_saved_scout
from test_r3_unified import RUN, ID, TEXT, NOW
import report_r313d_host as cli


class PrivateStagingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="bob-r313d-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.file = self.root/LAB_DIR/LAB_FILE
        create_legacy_fixture(self.file)
        self.marker = self.file.parent/LAB_MARKER
        self.marker.write_text(LAB_MARKER_VALUE,encoding="ascii")
        os.chmod(self.marker,0o600)
        self.source = self.root/"scout"
        make_saved_scout(self.source)
        self.action = Action(
            "comment",RUN,ID,"Bob's verified separate source reasoning.",TEXT)
        # A real saved Scout observation cannot be recycled as a new Bob
        # proposal when the same run was previously used in the old queue.
        # Relabel the original synthetic legacy fixture job only.
        with closing(self.connect()) as db:
            db.execute(
                "UPDATE decisions SET run_id='20261030T215000Z' "
                "WHERE run_id=?", (RUN,))
            db.execute(
                "UPDATE publish_jobs SET run_id='20261030T215000Z' "
                "WHERE run_id=?", (RUN,))

    def connect(self):
        return sqlite3.connect(self.file,isolation_level=None,timeout=4)

    def staged(self):
        with closing(self.connect()) as db:
            upgrade_private_copy(db)
            return migrate_marked_copy(db)

    def test_marked_private_upgrade_crash_then_repeat_preserves_every_history_row(self):
        with closing(self.connect()) as db:
            initial = _history_digest(db)
            old_attempts = _history_counts(db)
            upgrade_private_copy(db)
            after_b = _history_digest(db)
            with self.assertRaisesRegex(RuntimeError,"r313d_synthetic_crash"):
                migrate_marked_copy(db,inject_crash=True)
            self.assertEqual(_schema_shape(db),"absent")
            self.assertEqual(_history_digest(db),after_b)
            first = migrate_marked_copy(db)
            second = migrate_marked_copy(db)
            self.assertTrue(first["schema_added"])
            self.assertFalse(second["schema_added"])
            self.assertEqual(_schema_shape(db),"match")
            self.assertEqual(_history_digest(db),after_b)
            self.assertEqual(_history_counts(db),old_attempts)
            self.assertNotEqual(initial,after_b) # Four added OFF keys only.
            self.assertTrue(_off(db))
            self.assertFalse(first["real_r3_dispatch"])

    def test_existing_enabled_owner_value_blocks_schema_ddl(self):
        with closing(self.connect()) as db:
            upgrade_private_copy(db)
            db.execute("UPDATE publish_settings SET value='1' "
                       "WHERE name='r3_auto_enabled'")
            with self.assertRaisesRegex(ValueError,"unverified_private_schema_or_consent"):
                migrate_marked_copy(db)
            self.assertNotIn("r313c_action_envelopes",_tables(db))

    def test_missing_marker_and_wrong_fixture_path_refuse_ddl(self):
        with closing(self.connect()) as db:
            self.marker.write_text("WRONG",encoding="ascii")
            with self.assertRaisesRegex(ValueError,"invalid_upgrade_fixture_marker"):
                migrate_marked_copy(db)
            self.marker.write_text(LAB_MARKER_VALUE,encoding="ascii")
            os.chmod(self.marker,0o644)
            with self.assertRaisesRegex(ValueError,"untrusted_private_upgrade_fixture"):
                migrate_marked_copy(db)
            os.chmod(self.marker,0o600)
        # No accidental production DB name gets a writer.
        live = self.root/"activity-queue.sqlite3"
        create_legacy_fixture(live)
        with closing(sqlite3.connect(live)) as db:
            with self.assertRaisesRegex(ValueError,"untrusted_private_upgrade_fixture"):
                migrate_marked_copy(db)
        self.assertNotIn("r313c_action_envelopes",
                         sqlite3.connect(live).execute(
                             "SELECT name FROM sqlite_master").fetchall().__repr__())

    def test_partial_unknown_or_drifted_schema_refused(self):
        with closing(self.connect()) as db:
            upgrade_private_copy(db)
            db.execute("CREATE TABLE r313c_action_envelopes (source_run TEXT)")
            with self.assertRaisesRegex(ValueError,"partial_envelope_schema"):
                migrate_marked_copy(db)
            db.execute("DROP TABLE r313c_action_envelopes")
            migrate_marked_copy(db)
            db.execute("UPDATE r313c_schema_meta SET value='future-version'")
            with self.assertRaisesRegex(ValueError,"unknown_envelope_schema_version"):
                migrate_marked_copy(db)

    def test_exact_canonical_action_proposal_only_never_queues_or_posts(self):
        self.staged()
        with closing(self.connect()) as db:
            before = _history_counts(db)
            posted = propose_on_marked_copy(
                db,self.action,at=datetime(2026,10,30,23,25,tzinfo=timezone.utc))
            self.assertEqual(posted["state"],"proposed")
            self.assertFalse(posted["queued"])
            self.assertFalse(posted["dispatch_authorized"])
            self.assertEqual(_read_envelope(db,RUN),self.action)
            proposal=db.execute("SELECT state FROM r3_proposals "
                                "WHERE source_run=?", (RUN,)).fetchone()
            self.assertEqual(proposal,("proposed",))
            self.assertEqual(_history_counts(db),before)
            self.assertIsNone(db.execute(
                "SELECT run_id FROM publish_jobs WHERE run_id=?", (RUN,)
            ).fetchone())
            self.assertEqual(review_permission(
                db,mode="auto",source_run=RUN,seal_sha256="a"*64
            ).category,"refused")
            with self.assertRaisesRegex(ValueError,"duplicate_source_or_target"):
                propose_on_marked_copy(db,self.action,at=NOW)

    def test_source_drift_and_symlink_refused_before_any_proposal(self):
        self.staged()
        feed=self.source/("scout-feed-"+RUN+".json")
        feed.write_text('{"posts":[]}',encoding="utf-8")
        with closing(self.connect()) as db:
            with self.assertRaises(ValueError):
                propose_on_marked_copy(db,self.action,at=NOW)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM r3_proposals").fetchone()[0],0)
        make_saved_scout(self.source)
        renamed=self.source/"feed-old.json"
        feed.rename(renamed)
        feed.symlink_to(renamed)
        with closing(self.connect()) as db:
            with self.assertRaises(ValueError):
                propose_on_marked_copy(db,self.action,at=NOW)

    def test_stage_code_only_recovery_keeps_new_uncertain_history(self):
        self.staged()
        with closing(self.connect()) as db:
            start=_history_counts(db)
            db.execute(
                "INSERT INTO publish_jobs "
                "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                "created_at,attempted_at,updated_at)"
                " VALUES(?,?,?,?,'manual','uncertain',?,?,?)",
                ("20991231T235959Z","c"*64,
                 "ffffffff-ffff-4fff-8fff-ffffffffffff",
                 "SYNTHETIC ONLY","2099-12-31T23:59:59Z",
                 "2099-12-31T23:59:59Z","2099-12-31T23:59:59Z"))
            from bob_v08.r313b_upgrade_contract import code_only_rollback_review
            decision=code_only_rollback_review(db)
            self.assertFalse(decision["database_restore_allowed"])
            self.assertEqual(decision["retained_attempts"],start[1]+1)
            self.assertEqual(decision["retained_uncertain"],start[2]+1)

    def test_staged_private_snapshot_uses_real_sqlite_backup_including_wal(self):
        with closing(self.connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
                ("2026-10-30T23:00:00Z","committed_wal","synthetic"))
            report=cli._private_copy_staged(self.file)
            self.assertEqual(report["private_staged_upgrade"],"PASS")
            self.assertEqual(report["historical_attempts"],1)
            self.assertEqual(report["historical_uncertain"],1)
            self.assertTrue(report["new_synthetic_uncertain_attempt_retained"])
            self.assertTrue(report["private_copy_deleted"])
            self.assertFalse(report["live_database_changed"])
            self.assertNotIn("r313c_schema_meta",_tables(db))
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM publish_events").fetchone()[0],2)


class SourceGateTests(unittest.TestCase):
    def test_three_source_gates_are_off_and_no_release_installed(self):
        result=source_off_gate(ROOT)
        self.assertTrue(result["production_off_source"])
        self.assertEqual(result["gate_results"],["hard_off"]*3)
        self.assertFalse(result["installable"])
        from bob_r313c_adapter import production_dispatch_enabled
        self.assertFalse(production_dispatch_enabled())

    def test_candidate_turning_on_any_gate_blocks_off_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)
            paths=(
                "src/bin/bob-moltbook-publisher",
                "src/lib/bob/bob_r312_adapter.py",
                "src/lib/bob/bob_r313c_adapter.py",
            )
            for relative in paths:
                dest=copy/relative
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes((ROOT/relative).read_bytes())
            self.assertTrue(source_off_gate(copy)["production_off_source"])
            target=copy/paths[2]
            target.write_text(
                target.read_text().replace("R313C_REAL_DISPATCH = False",
                                           "R313C_REAL_DISPATCH = True"))
            self.assertFalse(source_off_gate(copy)["production_off_source"])

    def test_no_arbitrary_cli_paths_or_cutover_flag(self):
        self.assertEqual(cli.main(["--install"]),2)
        self.assertEqual(cli.main(["--db","/tmp/someone-elses-db"]),2)
        self.assertEqual(cli.main(["--enable-auto"]),2)
        self.assertNotIn("releases/current.json",
                         str(cli._private_copy_staged.__code__.co_consts))


if __name__ == "__main__":
    unittest.main()
