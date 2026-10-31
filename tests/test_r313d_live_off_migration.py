"""R3.13d OFF-only live migration contract tests: synthetic SQLite ONLY.

No actual systemd, Moltbook API, developer host, real backup or publisher.
The public --apply-off path refuses without authenticated owner/host gates.
"""
from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src"/"lib"/"bob"),
             str(ROOT/"scripts"),str(ROOT/"tests")]
from bob_v08.r313a_private_migration import _history_counts,_tables
from bob_v08.r313d_live_off_contract import (
    _apply_off_transaction,inspect_live_schema,
    _legacy_digest_without_new_settings,
)
from bob_v08.r313b_upgrade_contract import OFF_SETTINGS
from bob_v08.r313d_staging import _schema_shape,_off
from test_r35_migration_recovery import create_legacy_fixture
import r313d_live_off_migration as runner


class LiveOffCoreTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.file=Path(tmp.name)/"private-fixture"/"private-legacy.sqlite3"
        create_legacy_fixture(self.file)

    def con(self):
        return sqlite3.connect(self.file,timeout=4,isolation_level=None)

    def test_production_upgrade_preserves_every_existing_legacy_row(self):
        with closing(self.con()) as db:
            self.assertEqual(inspect_live_schema(db)["state"],"eligible")
            before=_legacy_digest_without_new_settings(db)
            counts=_history_counts(db)
            answer=_apply_off_transaction(db)
            self.assertTrue(answer["default_off"])
            self.assertFalse(answer["real_r3_dispatch"])
            self.assertFalse(answer["canary_authorized"])
            self.assertEqual(_schema_shape(db),"match")
            self.assertTrue(_off(db))
            self.assertEqual(_legacy_digest_without_new_settings(db),before)
            self.assertEqual(_history_counts(db),counts)
            self.assertEqual(inspect_live_schema(db)["state"],"ready")
            self.assertEqual(_apply_off_transaction(db)["state"],"off_schema_ready")
            self.assertEqual(_legacy_digest_without_new_settings(db),before)

    def test_injected_crash_before_commit_keeps_old_queue_and_no_new_schema(self):
        with closing(self.con()) as db:
            old=_legacy_digest_without_new_settings(db)
            oldcount=_history_counts(db)
            with self.assertRaisesRegex(RuntimeError,
                                        "r313d_live_off_simulated_precommit_crash"):
                _apply_off_transaction(db,inject_crash=True)
            self.assertEqual(_legacy_digest_without_new_settings(db),old)
            self.assertEqual(_history_counts(db),oldcount)
            self.assertNotIn("r3_proposals",_tables(db))
            self.assertNotIn("r313c_action_envelopes",_tables(db))
            self.assertEqual(inspect_live_schema(db)["state"],"eligible")

    def test_old_legacy_auto_can_be_on_without_r3_owner_permission(self):
        with closing(self.con()) as db:
            db.execute("UPDATE publish_settings SET value='1'"
                       " WHERE name='auto_enabled'")
            self.assertEqual(inspect_live_schema(db)["state"],"eligible")
            _apply_off_transaction(db)
            self.assertEqual(db.execute("SELECT value FROM publish_settings "
                                       "WHERE name='auto_enabled'").fetchone(),("1",))
            for name,value in OFF_SETTINGS.items():
                self.assertEqual(db.execute(
                    "SELECT value FROM publish_settings WHERE name=?",
                    (name,)).fetchone(),(value,))

    def test_existing_owner_enabled_refuses_without_migration(self):
        with closing(self.con()) as db:
            db.execute("INSERT INTO publish_settings VALUES"
                       "('r3_manual_enabled','1')")
            self.assertEqual(inspect_live_schema(db)["state"],"refused")
            with self.assertRaises(ValueError):
                _apply_off_transaction(db)
            self.assertNotIn("r3_proposals",_tables(db))

    def test_partial_and_unknown_future_schema_refuse(self):
        with closing(self.con()) as db:
            db.execute("CREATE TABLE r3_proposals(source_run TEXT)")
            self.assertEqual(inspect_live_schema(db)["state"],"refused")
            with self.assertRaises(ValueError):
                _apply_off_transaction(db)
        with closing(self.con()) as db:
            db.execute("DROP TABLE r3_proposals")
            _apply_off_transaction(db)
            db.execute("UPDATE r313c_schema_meta SET value='future'")
            self.assertEqual(inspect_live_schema(db)["state"],"refused")

    def test_future_uncertain_send_retained_and_old_schema_not_restored(self):
        with closing(self.con()) as db:
            _apply_off_transaction(db)
            old=_history_counts(db)
            db.execute(
                "INSERT INTO publish_jobs "
                "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                "created_at,attempted_at,updated_at)"
                "VALUES(?,?,?,?,'manual','uncertain',?,?,?)",
                ("20991231T235959Z","f"*64,
                 "ffffffff-ffff-4fff-8fff-ffffffffffff","synthetic only",
                 "2099-12-31T23:59:59Z","2099-12-31T23:59:59Z",
                 "2099-12-31T23:59:59Z"))
            newer=_history_counts(db)
            self.assertEqual(newer[1],old[1]+1)
            self.assertEqual(newer[2],old[2]+1)
            self.assertEqual(inspect_live_schema(db)["state"],"ready")
            self.assertEqual(_apply_off_transaction(db)["state"],"off_schema_ready")
            self.assertEqual(_history_counts(db),newer)


class OperatorGatesTests(unittest.TestCase):
    @staticmethod
    def phase_evidence(*, migrated=False, extra_blocker=False):
        blockers=(["additive_schema_not_empty"] if migrated else [])
        if extra_blocker:
            blockers.append("queue_file_not_private")
        return {
            "reviewed_off_gates":{"production_off_source":True},
            "publisher":{
                "effective_unit_shape":"reviewed_shape",
                "installed_file":"owner_controlled_regular",
                "updater_registry":"verified_registry_hash",
                "review_blockers":[],
            },
            "host":{
                "legacy_schema":"match",
                "private_copy_eligible":not migrated and not extra_blocker,
                "additive_schema":("existing_needs_review" if migrated
                                   else "absent"),
                "r3_settings":"explicit_off" if migrated else "absent_off",
                "review_blockers":blockers,
            },
        }

    def test_post_migration_attestation_only_accepts_exact_completed_off_state(self):
        good=self.phase_evidence(migrated=True)
        ready={"state":"ready","attempts":23,"uncertain":0}
        self.assertTrue(runner._host_phase_accepted(good,ready,"complete"))
        self.assertFalse(runner._host_phase_accepted(good,ready,"prepared"))
        self.assertFalse(runner._host_phase_accepted(good,ready,"absent"))
        self.assertFalse(runner._host_phase_accepted(
            good,{"state":"refused"},"complete"))
        wrong=self.phase_evidence(migrated=True)
        wrong["host"]["r3_settings"]="present_requires_owner_review"
        self.assertFalse(runner._host_phase_accepted(wrong,ready,"complete"))
        wrong=self.phase_evidence(migrated=True)
        wrong["publisher"]["updater_registry"]="registry_hash_mismatch"
        self.assertFalse(runner._host_phase_accepted(wrong,ready,"complete"))
        wrong=self.phase_evidence(migrated=True,extra_blocker=True)
        self.assertFalse(runner._host_phase_accepted(wrong,ready,"complete"))
        wrong=self.phase_evidence(migrated=True)
        wrong["reviewed_off_gates"]["production_off_source"]=False
        self.assertFalse(runner._host_phase_accepted(wrong,ready,"complete"))

    def test_pre_migration_private_stage_still_requires_exact_absent_schema(self):
        old=self.phase_evidence(migrated=False)
        self.assertTrue(runner._host_phase_accepted(
            old,{"state":"eligible"},"absent"))
        self.assertFalse(runner._host_phase_accepted(
            old,{"state":"ready"},"complete"))
        self.assertFalse(runner._host_phase_accepted(
            old,{"state":"eligible"},"complete"))
        wrong=self.phase_evidence(migrated=False,extra_blocker=True)
        self.assertFalse(runner._host_phase_accepted(
            wrong,{"state":"eligible"},"absent"))

    def test_fixed_systemd_drain_requires_all_inactive_and_timer_disabled(self):
        expected={
            ("bob-moltbook-publisher.timer","is-active"):"inactive",
            ("bob-moltbook-publisher.service","is-active"):"inactive",
            ("bob-activity-manager.service","is-active"):"inactive",
            ("bob-moltbook-publisher.timer","is-enabled"):"disabled",
        }
        self.assertTrue(runner._drained(probe=lambda unit,mode:expected[(unit,mode)]))
        expected[("bob-moltbook-publisher.timer","is-enabled")]="enabled"
        self.assertFalse(runner._drained(probe=lambda unit,mode:expected[(unit,mode)]))
        expected[("bob-moltbook-publisher.timer","is-enabled")]="disabled"
        expected[("bob-moltbook-publisher.service","is-active")]="active"
        self.assertFalse(runner._drained(probe=lambda unit,mode:expected[(unit,mode)]))

    def test_untrusted_gate_refuses_before_backup_or_db_write(self):
        with patch.object(runner,"review",return_value={
            "eligible_for_off_migration":False}):
            with patch.object(runner,"create_verified_backup") as backup:
                with self.assertRaises(ValueError):
                    runner._apply_off()
                backup.assert_not_called()

    def test_no_arbitrary_cli_or_unconfirmed_migration(self):
        self.assertEqual(runner.main(["--database","/tmp/other.sqlite3"]),2)
        self.assertEqual(runner.main(["--apply"]),2)
        self.assertEqual(runner.main(["--enable-posting"]),2)

if __name__=="__main__":
    unittest.main()
