"""Offline R3.0 read-only cutover inventory: no network, real service or write."""
from __future__ import annotations
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_r3_cutover_inventory as r3


class UnitTests(unittest.TestCase):
    def test_allowlisted_systemd_and_sanitized_values(self):
        calls = []
        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            return Mock(returncode=0, stdout=(
                "LoadState=loaded\nActiveState=active\nSubState=waiting\n"
                "UnitFileState=enabled\nResult=success\n"
                "Environment=MOLTBOOK_API_KEY=do-not-echo\n"))
        data = r3.unit_facts("user", "bob-v08-shadow.timer", run=fake_run)
        self.assertEqual(data["active"], "active")
        self.assertEqual(data["enabled"], "enabled")
        self.assertNotIn("MOLTBOOK_API_KEY", json.dumps(data))
        self.assertNotIn("Environment", json.dumps(data))
        self.assertEqual(calls[0][0][0:2], ["systemctl", "--user"])
        self.assertEqual(calls[0][1]["timeout"], 3)
        with self.assertRaisesRegex(ValueError, "unrecognized_cutover_unit"):
            r3.unit_facts("user", "evil.service", run=fake_run)
        self.assertEqual(len(calls), 1)

    def test_invalid_and_unavailable_systemd_properties_fail_closed(self):
        def bogus(command, **kwargs):
            return Mock(returncode=0, stdout="ActiveState=whatever\nUnitFileState=enabled\n"
                        "Result=custom-secret-message\n")
        data = r3.unit_facts("user", "bob-v08-shadow.service", run=bogus)
        self.assertEqual(data["active"], "unknown")
        self.assertEqual(data["result"], "unknown")
        self.assertEqual(data["enabled"], "enabled")
        self.assertEqual(r3.unit_facts("system", "bob-moltbook-scout.timer",
                                      run=lambda *_a, **_kw: Mock(
                                          returncode=1, stdout="failed"))["active"], "unknown")

    def test_no_unlisted_unit_names(self):
        self.assertEqual(len(set(r3.UNITS)), len(r3.UNITS))
        for scope, unit in r3.UNITS:
            self.assertIn(scope, ("user", "system"))
            self.assertTrue(unit.startswith(("bob-", "openclaw-")))
            self.assertTrue(unit.endswith((".timer", ".service")))


class QueueTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.database = self.root / "queue.sqlite3"
        self.paused = self.root / "paused"
        with sqlite3.connect(self.database) as db:
            db.executescript(
                "CREATE TABLE publish_jobs (mode TEXT,state TEXT,attempted_at TEXT);"
                "CREATE TABLE publish_settings (name TEXT PRIMARY KEY,value TEXT);")
            db.executemany("INSERT INTO publish_jobs VALUES(?,?,?)", [
                ("manual", "queued", None), ("auto", "failed", None),
                ("auto", "uncertain", "2026-10-30T00:00:00+00:00"),
                ("raw-MOLTBOOK_SECRET", "junk-secret", None)])
            db.execute("INSERT INTO publish_settings VALUES('auto_enabled','1')")
            # Actual policy remains the source of truth for values and ranges.

    def test_metadata_only_uses_readonly_db_and_limits(self):
        before = self.database.read_bytes()
        result = r3.queue_facts(self.database, paused=self.paused)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode_counts"]["manual/queued"], 1)
        self.assertEqual(result["mode_counts"]["auto/failed"], 1)
        self.assertEqual(result["mode_counts"]["unknown/unknown"], 1)
        self.assertEqual(result["attempts_with_timestamp"], 1)
        self.assertEqual(result["auto_enabled"], "enabled")
        self.assertEqual(result["policy_status"], "valid")
        self.assertEqual(result["policy_limits"]["comment_daily"], 2)
        self.assertNotIn("MOLTBOOK_SECRET", json.dumps(result))
        self.assertEqual(self.database.read_bytes(), before)
        self.assertFalse((self.root / "queue.sqlite3-wal").exists())

    def test_untrusted_settings_cannot_become_authority(self):
        with sqlite3.connect(self.database) as db:
            db.execute("INSERT INTO publish_settings VALUES('activity_limit_comment_daily','100000')")
            db.execute("UPDATE publish_settings SET value='junk' WHERE name='auto_enabled'")
        result = r3.queue_facts(self.database, paused=self.paused)
        self.assertEqual(result["auto_enabled"], "invalid")
        self.assertEqual(result["policy_status"], "invalid")
        self.assertEqual(result["policy_limits"], {})

    def test_missing_and_symlink_database_are_never_created_or_followed(self):
        absent = self.root / "absent.sqlite3"
        self.assertEqual(r3.queue_facts(absent, paused=self.paused)["status"], "unavailable")
        self.assertFalse(absent.exists())
        link = self.root / "linked.sqlite3"
        link.symlink_to(self.database)
        self.assertEqual(r3.queue_facts(link, paused=self.paused)["status"], "unavailable")
        self.paused.symlink_to(self.database)
        self.assertEqual(r3.queue_facts(self.database, paused=self.paused)["pause"],
                         "unavailable")

    def test_root_report_cannot_authorize_cutover(self):
        def test_unit(scope, unit):
            return {"scope": scope, "unit": unit, "active": "unknown"}
        report = r3.inventory(queue_path=self.database, paused=self.paused,
                              get_unit=test_unit)
        self.assertFalse(report["cutover_authorized"])
        self.assertEqual(report["authority"], "design_only_no_publishing_or_cutover")
        self.assertEqual(len(report["service_status"]), len(r3.UNITS))
        self.assertNotIn("draft_comment", json.dumps(report))
        self.assertNotIn("MOLTBOOK_SECRET", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
