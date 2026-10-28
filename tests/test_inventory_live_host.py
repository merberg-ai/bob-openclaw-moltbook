"""Offline, synthetic regression tests for the read-only baseline collector."""

import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inventory_live_host as inventory


class BaselineInventoryTests(unittest.TestCase):
    def test_collects_hashes_and_schema_without_private_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            bindir = home / ".local/bin"
            units = home / ".config/systemd/user"
            db = home / ".config/moltbook/activity-queue.sqlite3"
            bindir.mkdir(parents=True)
            units.mkdir(parents=True)
            db.parent.mkdir(parents=True)

            (bindir / "bobctl").write_text("private-mock-token-in-script\n")
            (bindir / "bob-activity-manager").write_text("print('mock')\n")
            (bindir / "bob-secret-key").write_text("dont-read-me\n")
            (bindir / "unrelated").write_text("unrelated\n")
            if hasattr(os, "symlink"):
                (bindir / "bob-linked").symlink_to(bindir / "bobctl")
            (units / "bob-activity-manager.service").write_text(
                "Environment=MOLTBOOK_TOKEN=hidden-unit-token\n"
            )
            dropin = units / "bob-activity-manager.service.d"
            dropin.mkdir()
            (dropin / "10-override.conf").write_text(
                "Environment=PRIVATE_PASSWORD=hidden-dropin-secret\n"
            )
            with sqlite3.connect(db) as conn:
                conn.execute(
                    "CREATE TABLE posts (id INTEGER PRIMARY KEY, content TEXT "
                    "DEFAULT 'secret-default-text')"
                )
                conn.execute(
                    "INSERT INTO posts(content) VALUES ('secret-row-text')"
                )
                conn.execute("PRAGMA user_version=6")

            report = inventory.build_inventory(
                home, [bindir], [units], db, include_unit_states=False
            )
            raw = json.dumps(report)
            self.assertEqual(report["sqlite_schema"]["status"], "read_only_schema")
            self.assertEqual(report["sqlite_schema"]["user_version"], 6)
            self.assertEqual(
                report["sqlite_schema"]["tables"][0]["columns"][1]["name"],
                "content",
            )
            self.assertTrue(any(p["path"].endswith("bobctl") for p in report["code_files"]))
            self.assertTrue(all("sha256" in p for p in report["code_files"]))
            self.assertEqual(len(report["code_files"]), 2)
            self.assertEqual(len(report["unit_files"]), 2)
            for secret in (
                "private-mock-token-in-script", "dont-read-me",
                "hidden-unit-token", "hidden-dropin-secret",
                "secret-default-text", "secret-row-text",
            ):
                self.assertNotIn(secret, raw)

    def test_absent_database_and_private_report_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            missing = home / "missing.sqlite3"
            self.assertEqual(
                inventory.inventory_sqlite_schema(missing)["status"], "not_found"
            )
            folder = home / "private"
            path = inventory.write_private_report({"test": True}, folder)
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text()), {"test": True})
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_refuses_public_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "public"
            folder.mkdir(mode=0o755)
            folder.chmod(0o755)
            with self.assertRaises(PermissionError):
                inventory.write_private_report({}, folder)

    def test_rejects_symlinked_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir(mode=0o700)
            link = root / "linked"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(PermissionError):
                inventory.write_private_report({}, link)

    def test_filters_names_without_reading_any_config(self):
        self.assertTrue(inventory.is_code_candidate(Path("bobctl")))
        self.assertTrue(inventory.is_code_candidate(Path("bob_moltbook_api.py")))
        self.assertTrue(inventory.is_code_candidate(Path("bob-original-worker")))
        self.assertFalse(inventory.is_code_candidate(Path("bob-token")))
        self.assertFalse(inventory.is_code_candidate(Path("openclaw.json")))
        self.assertFalse(inventory.is_code_candidate(Path("bob-backup.sh")))


if __name__ == "__main__":
    unittest.main()
