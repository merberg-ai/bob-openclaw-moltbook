"""Small offline acceptance set for the version-aware Bob updater.

No network, no installed files, no systemd, no DB modifications.
"""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bob_release_updater as updater
import bootstrap_bob_updater as bootstrap


class UpdaterSmoke(unittest.TestCase):
    def test_initial_manifest_is_noop(self):
        manifest = updater.manifest(ROOT)
        self.assertEqual(manifest["release"], "v0.7.2-main-channel")
        self.assertEqual(manifest["from"], manifest["release"])
        self.assertEqual(manifest["files"], [])
        self.assertFalse(manifest["restart_manager"])

    def test_bobctl_command_is_exact_and_bootstrap_is_pinned(self):
        before = bootstrap.source(bootstrap.OLD_BOBCTL)
        after = bootstrap.source(bootstrap.NEW_BOBCTL)
        self.assertNotEqual(before, after)
        self.assertIn(b'if name == "update":', after)
        self.assertNotIn(b'if name == "update":', before)
        self.assertIn(b'bob-release-updater', after)

    def test_malformed_release_is_refused(self):
        original = updater.Path
        self.assertIsNotNone(original)
        self.assertFalse(updater.TARGET.fullmatch("../.ssh/id_rsa"))
        self.assertTrue(updater.TARGET.fullmatch("bobctl"))
        self.assertTrue(updater.TARGET.fullmatch("bob-release-updater"))
        self.assertTrue(updater.TARGET.fullmatch("bob_status_view.py"))
        self.assertFalse(updater.TARGET.fullmatch("credentials.json"))

    def test_core_updater_has_no_publish_or_auto_start_paths(self):
        engine = bootstrap.source(bootstrap.UPDATER_SOURCE)
        self.assertNotIn(b"publisher-run", engine)
        self.assertNotIn(b"bob-moltbook-publisher.service", engine)
        self.assertIn(b"mode=ro", (ROOT / "scripts/backup_live_sqlite.py").read_bytes())
        self.assertIn(b'["systemctl", "--user", "restart", "bob-activity-manager.service"]', engine)

    def test_initial_manager_build_is_available(self):
        manager, nav = bootstrap.builder.build()
        self.assertIn(b"Comments without confirmed IDs", manager)
        self.assertIn(b"/system/status", manager)
        self.assertIn(b"/settings", nav)
        compile(manager, "bob-activity-manager", "exec")


if __name__ == "__main__":
    unittest.main()
