"""R3.13b isolated upgrade, consent, and publisher executable audit tests."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
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
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT / "tests")]

from bob_v08.r313b_upgrade_contract import (
    LAB_FILE, LAB_DIR, LAB_MARKER, LAB_MARKER_VALUE,
    OFF_SETTINGS, owner_controls, review_permission, upgrade_private_copy,
    code_only_rollback_review,
)
from bob_v08 import r313b_install_attestation as audit
from bob_v08 import r313a_private_migration as base
from test_r35_migration_recovery import create_legacy_fixture
import report_r313b_host as cli


class PrivateUpgradeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="bob-r313b-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.dbfile = self.root / LAB_DIR / LAB_FILE
        create_legacy_fixture(self.dbfile)
        self.marker = self.dbfile.parent / LAB_MARKER
        self.marker.write_text(LAB_MARKER_VALUE, encoding="ascii")
        os.chmod(self.marker, 0o600)

    def connect(self):
        return sqlite3.connect(self.dbfile, isolation_level=None)

    def test_default_off_and_idempotent_schema_preserve_legacy_attempts(self):
        with closing(self.connect()) as db:
            before = base._history_counts(db)
            result = upgrade_private_copy(db)
            self.assertTrue(result["schema_added"])
            self.assertEqual(result["historical_attempts"], 1)
            self.assertEqual(result["historical_uncertain"], 1)
            self.assertTrue(result["existing_legacy_rows_preserved"])
            self.assertEqual(base._history_counts(db), before)
            self.assertEqual(owner_controls(db),
                             dict(manual="off", automatic="off", authority="none"))
            for k, value in OFF_SETTINGS.items():
                self.assertEqual(db.execute(
                    "SELECT value FROM publish_settings WHERE name=?",
                    (k,)).fetchone(), (value,))
            second = upgrade_private_copy(db)
            self.assertFalse(second["schema_added"])
            self.assertEqual(base._history_counts(db), before)
            self.assertFalse(second["network_dispatch_authorized"])

    def test_crash_before_commit_rolls_back_tables_and_off_keys(self):
        with closing(self.connect()) as db:
            before = base._history_digest(db)
            with self.assertRaisesRegex(RuntimeError, "synthetic_crash"):
                upgrade_private_copy(db, inject_crash=True)
            self.assertEqual(base._history_digest(db), before)
            self.assertFalse(base.ADD_NAMES & base._tables(db))
            for key in OFF_SETTINGS:
                self.assertIsNone(db.execute(
                    "SELECT value FROM publish_settings WHERE name=?",
                    (key,)).fetchone())
            self.assertTrue(upgrade_private_copy(db)["schema_added"])

    def test_missing_corrupt_or_unsafe_fixture_cannot_migrate(self):
        with closing(self.connect()) as db:
            self.marker.write_text("wrong marker", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "invalid_upgrade_fixture_marker"):
                upgrade_private_copy(db)
            self.marker.write_text(LAB_MARKER_VALUE, encoding="ascii")
            os.chmod(self.marker, 0o644)
            with self.assertRaisesRegex(ValueError, "untrusted_private_upgrade_fixture"):
                upgrade_private_copy(db)
            os.chmod(self.marker, 0o600)
        alias = self.root / "activity-queue.sqlite3"
        alias.symlink_to(self.dbfile)
        with closing(sqlite3.connect(alias)) as db:
            with self.assertRaisesRegex(ValueError, "untrusted_private_upgrade_fixture"):
                upgrade_private_copy(db)

    def test_existing_opt_in_even_if_legacy_auto_is_on_refuses_migration(self):
        with closing(self.connect()) as db:
            db.execute("UPDATE publish_settings SET value='1' WHERE name='auto_enabled'")
            db.execute("INSERT INTO publish_settings VALUES('r3_auto_enabled','1')")
            before = base._history_digest(db)
            with self.assertRaisesRegex(ValueError, "owner_setting_needs_review"):
                upgrade_private_copy(db)
            self.assertEqual(base._history_digest(db), before)
            self.assertFalse(base.ADD_NAMES & base._tables(db))

    def test_preexisting_off_values_are_kept_not_overwritten(self):
        with closing(self.connect()) as db:
            db.execute("INSERT INTO publish_settings VALUES('r3_comment_dial','off')")
            before = base._history_digest(db)
            self.assertTrue(upgrade_private_copy(db)["schema_added"])
            self.assertEqual(db.execute(
                "SELECT value FROM publish_settings WHERE name='r3_comment_dial'"
            ).fetchone(), ("off",))
            self.assertFalse(upgrade_private_copy(db)["schema_added"])
            self.assertEqual(base._history_counts(db), (2, 1, 1))
            # No existing decision/queue/attempt row ever changed.
            old = db.execute("SELECT COUNT(*) FROM publish_jobs").fetchone()[0]
            self.assertEqual(old, 2)
            self.assertNotEqual(base._history_digest(db), before)  # new OFF keys only

    def test_unknown_partial_r3_schema_refused_without_changes(self):
        with closing(self.connect()) as db:
            db.execute("CREATE TABLE r3_unknown_ledger(id INTEGER)")
            with self.assertRaisesRegex(ValueError, "unknown_r3_schema"):
                upgrade_private_copy(db)
            db.execute("DROP TABLE r3_unknown_ledger")
            db.execute("CREATE TABLE r3_proposals(source_run TEXT)")
            with self.assertRaisesRegex(ValueError, "partial_r3_schema"):
                upgrade_private_copy(db)

    def test_manual_requires_distinct_flag_dial_and_exact_seal(self):
        run = "20261030T235959Z"
        digest = "a"*64
        with closing(self.connect()) as db:
            upgrade_private_copy(db)
            db.execute("INSERT INTO r3_owner_approvals VALUES(?,?,?,?)",
                       (run, digest, "approved", "2026-10-30T23:59:59Z"))
            self.assertEqual(review_permission(
                db, mode="manual", source_run=run,
                seal_sha256=digest).category, "refused")
            db.execute("UPDATE publish_settings SET value='propose' "
                       "WHERE name='r3_comment_dial'")
            self.assertEqual(review_permission(
                db, mode="manual", source_run=run,
                seal_sha256=digest).category, "refused")
            db.execute("UPDATE publish_settings SET value='1' "
                       "WHERE name='r3_manual_enabled'")
            self.assertEqual(review_permission(
                db, mode="manual", source_run=run,
                seal_sha256="b"*64).category, "refused")
            passed = review_permission(db, mode="manual", source_run=run,
                                       seal_sha256=digest)
            self.assertEqual(passed.category, "reviewed")
            self.assertTrue(passed.owner_permission_observed)
            self.assertFalse(passed.dispatch_authorized)
            self.assertFalse(passed.acted)
            db.execute("UPDATE r3_owner_approvals SET decision='rejected'")
            self.assertEqual(review_permission(
                db, mode="manual", source_run=run,
                seal_sha256=digest).category, "refused")

    def test_auto_needs_new_and_old_opt_in_and_newer_source(self):
        run = "20261030T235959Z"
        with closing(self.connect()) as db:
            upgrade_private_copy(db)
            db.execute("UPDATE publish_settings SET value='auto' "
                       "WHERE name='r3_comment_dial'")
            db.execute("UPDATE publish_settings SET value='1' "
                       "WHERE name='r3_auto_enabled'")
            db.execute("UPDATE publish_settings SET value='2026-10-30T23:00:00Z' "
                       "WHERE name='r3_auto_since'")
            self.assertEqual(review_permission(
                db, mode="auto", source_run=run,
                seal_sha256="f"*64).category, "refused")
            db.execute("UPDATE publish_settings SET value='1' "
                       "WHERE name='auto_enabled'")
            passed = review_permission(db, mode="auto", source_run=run,
                                       seal_sha256="f"*64)
            self.assertEqual(passed.category, "reviewed")
            self.assertFalse(passed.dispatch_authorized)
            db.execute("UPDATE publish_settings SET value='2026-11-01T00:00:00Z' "
                       "WHERE name='r3_auto_since'")
            self.assertEqual(review_permission(
                db, mode="auto", source_run=run,
                seal_sha256="f"*64).reason, "source_precedes_r3_opt_in")
            db.execute("UPDATE publish_settings SET value='not-a-time' "
                       "WHERE name='r3_auto_since'")
            self.assertEqual(review_permission(
                db, mode="auto", source_run=run,
                seal_sha256="f"*64).reason, "owner_permission_unverifiable")

    def test_code_only_rollback_does_not_rewind_new_uncertain_attempt(self):
        with closing(self.connect()) as db:
            upgrade_private_copy(db)
            db.execute("INSERT INTO publish_jobs(run_id,approval_sha256,post_id,"
                       "draft_comment,mode,state,created_at,attempted_at,updated_at) "
                       "VALUES(?,?,?,?,'auto','uncertain',?,?,?)",
                       ("20991231T235959Z", "c"*64,
                        "ffffffff-ffff-4fff-8fff-ffffffffffff",
                        "synthetic only", "2099-12-31T23:59:59Z",
                        "2099-12-31T23:59:59Z", "2099-12-31T23:59:59Z"))
            original = base._history_digest(db)
            outcome = code_only_rollback_review(db)
            self.assertFalse(outcome["database_restore_allowed"])
            self.assertEqual((outcome["retained_attempts"],
                              outcome["retained_uncertain"]), (2,2))
            self.assertEqual(base._history_digest(db), original)

    def test_end_to_end_synthetic_online_backup_with_committed_wal(self):
        with closing(self.connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
                       ("2026-10-30T12:00:00Z", "committed", "synthetic WAL"))
            db.commit()
            snapshot = cli._private_upgrade_rehearsal(self.dbfile)
            self.assertEqual(snapshot["private_upgrade"], "PASS")
            self.assertTrue(snapshot["idempotent"])
            self.assertTrue(snapshot["default_off_owner_controls"])
            self.assertTrue(snapshot["code_only_rollback_preserved_new_history"])
            self.assertEqual(snapshot["original_attempts"], 1)
            self.assertEqual(snapshot["original_uncertain"], 1)
            self.assertFalse(snapshot["live_database_modified"])
            self.assertFalse(snapshot["cutover_authorized"])
            self.assertNotIn("r3_proposals", base._tables(db))
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM publish_events").fetchone()[0], 2)


class PublisherAttestationTests(unittest.TestCase):
    SERVICE = """# /owner/.config/systemd/user/bob-moltbook-publisher.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /secure/bob-moltbook-publisher
Environment=TOKEN=NEVER_ECHO
"""
    TIMER = """[Timer]
Unit=bob-moltbook-publisher.service
OnUnitActiveSec=1min
"""

    def fake_units(self, unit):
        self.assertIn(unit, (audit.SERVICE, audit.TIMER))
        return self.SERVICE if unit == audit.SERVICE else self.TIMER

    def test_sanitized_effective_unit_and_binary_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bob-moltbook-publisher"
            src.write_bytes(b"candidate")
            with patch.object(audit, "_safe_binary", return_value=b"legacy"):
                with patch.object(audit, "_registry_match",
                                  return_value="not_registry_tracked"):
                    data = audit.attest(unit_reader=self.fake_units,
                                        uid=os.geteuid(), home=Path(tmp),
                                        candidate_source=src)
            self.assertEqual(data["effective_unit_shape"], "reviewed_shape")
            self.assertEqual(data["installed_file"], "owner_controlled_regular")
            self.assertEqual(data["current_next_candidate_match"],
                             "different_legacy_release_expected")
            self.assertFalse(data["cutover_authorized"])
            self.assertNotIn("TOKEN", json.dumps(data))
            self.assertNotIn("/secure/", json.dumps(data))

    def test_execstart_reset_and_unknown_extra_commands_block(self):
        service = self.SERVICE + """
# /owner/.config/systemd/user/bob-moltbook-publisher.service.d/override.conf
[Service]
ExecStart=
ExecStart=/usr/bin/python3 /secure/bob-moltbook-publisher
"""
        self.assertEqual(audit._exec_path(service).name, "bob-moltbook-publisher")
        hostile = self.SERVICE.replace(
            "/secure/bob-moltbook-publisher",
            "/usr/bin/bash -c /secure/bob-moltbook-publisher")
        def run(name):
            return hostile if name == audit.SERVICE else self.TIMER
        with patch.object(audit, "_safe_binary", side_effect=AssertionError):
            data = audit.attest(unit_reader=run, uid=os.geteuid(),
                                home=Path("/nonexistent"))
        self.assertIn("installed_publisher_source_or_unit_needs_review",
                      data["review_blockers"])
        self.assertFalse(data["cutover_authorized"])

    def test_real_binary_reader_rejects_symlink_and_writable_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bob-moltbook-publisher"
            source.write_bytes(b"#!/usr/bin/python3\n")
            os.chmod(source, 0o666)
            with self.assertRaises(ValueError):
                audit._safe_binary(source, uid=os.geteuid())
            os.chmod(source, 0o600)
            alias = Path(tmp) / "alias"
            alias.symlink_to(source)
            with self.assertRaises(ValueError):
                audit._safe_binary(alias, uid=os.geteuid())

    def test_registry_hash_mismatch_blocks_attestation(self):
        with patch.object(audit, "_safe_binary", return_value=b"legacy"):
            with patch.object(audit, "_registry_match",
                              return_value="registry_hash_mismatch"):
                data = audit.attest(unit_reader=self.fake_units,
                                    uid=os.geteuid(), home=Path("/home/fixture"))
        self.assertEqual(data["updater_registry"], "registry_hash_mismatch")
        self.assertTrue(data["review_blockers"])
        self.assertFalse(data["cutover_authorized"])

    def test_invalid_cli_and_source_file_have_no_write_or_http_paths(self):
        self.assertEqual(cli.main(["--database", "/tmp/queue.sqlite3"]), 2)
        self.assertEqual(cli.main(["--enable"]), 2)
        for module in (cli, audit):
            source = inspect.getsource(module)
            for forbidden in ("api_key(", "urllib.request", "requests.post",
                              "systemctl restart", "systemctl enable",
                              "systemctl stop", "os.system("):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
