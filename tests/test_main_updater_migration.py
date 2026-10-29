"""Three small offline checks for the one-time canonical main updater migration."""
from __future__ import annotations
import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bob_release_updater as updater
import migrate_bob_updater_to_main as migration


class MainMigrationChecks(unittest.TestCase):
    def test_migration_updates_only_the_trusted_branch(self):
        old = migration.inspected_source(migration.OLD)
        new = migration.inspected_source(migration.NEW)
        self.assertEqual(new, old.replace(
            b'BRANCH = "feature/v0.7.1-navigation"', b'BRANCH = "main"', 1))
        self.assertEqual(updater.BRANCH, "main")

    def test_main_release_chain_keeps_migration_baseline(self):
        plan = updater.manifest(ROOT)
        self.assertTrue(plan["from"])
        if plan["release"] == migration.NEW_RELEASE:
            self.assertEqual(plan["files"], [])
            self.assertFalse(plan["restart_manager"])
        else:
            self.assertNotEqual(plan["release"], plan["from"])
            self.assertTrue(plan["files"])

    def test_read_only_mode_never_invokes_apply(self):
        with patch.object(migration, "plan", return_value={"old_checkout": "/mock/old"}), \
             patch.object(migration, "apply", side_effect=AssertionError("unexpected mutation")), \
             patch.object(sys, "argv", ["migrate_bob_updater_to_main.py"]), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(migration.main(), 0)
        self.assertIn("READY (read-only)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
