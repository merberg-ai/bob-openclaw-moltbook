"""Focused checks for trusted-console reset and responsive Settings hotfix."""
from __future__ import annotations
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src/lib/bob"))
import bob_dashboard_auth as auth
import set_dashboard_login as cli
import build_v072_settings_candidate as builder


class ConsoleReset(unittest.TestCase):
    def test_new_username_and_password_take_effect_without_restart(self):
        with tempfile.TemporaryDirectory(prefix="bob-login-test-") as temp:
            home = Path(temp)
            home.chmod(0o700)
            path = home / "lan-auth.json"
            path.write_text(json.dumps({"username": "previous", "password": "previous-secret-password123",
                                        "unrelated": "keep-this"}))
            path.chmod(0o600)
            cli.reset_login(path, "updated-user", "new-secret-password4567")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(auth.load(path)["unrelated"], "keep-this")
            old = "Basic " + base64.b64encode(b"previous:previous-secret-password123").decode()
            new = "Basic " + base64.b64encode(b"updated-user:new-secret-password4567").decode()
            self.assertFalse(auth.authorized(path, old))
            self.assertTrue(auth.authorized(path, new))

    def test_weak_password_refused_without_file_change(self):
        with tempfile.TemporaryDirectory(prefix="bob-login-test-") as temp:
            home = Path(temp)
            home.chmod(0o700)
            path = home / "lan-auth.json"
            path.write_text(json.dumps({"username": "previous", "password": "previous-secret-password123"}))
            path.chmod(0o600)
            old = path.read_bytes()
            with self.assertRaises(auth.CredentialError):
                cli.reset_login(path, "user", "short")
            self.assertEqual(old, path.read_bytes())


class SettingsVisualFix(unittest.TestCase):
    def test_same_navigation_and_only_settings_form_changes(self):
        before, old_nav = builder.build(styled=False)
        after, new_nav = builder.build(styled=True)
        self.assertEqual(old_nav, new_nav)
        self.assertNotEqual(before, after)
        self.assertIn(b"bob-settings-form", after)
        self.assertIn(b"bob-settings-field", after)
        self.assertIn(b"v0.7.2", after)
        for route in (b"/settings", b"/originals", b"/system/status"):
            self.assertIn(route, after)
        compile(after, "bob-activity-manager", "exec")

if __name__ == "__main__":
    unittest.main()
