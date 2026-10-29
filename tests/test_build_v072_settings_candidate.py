"""v0.7.2 Settings composition checks; no production files or credentials."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_v072_settings_candidate as builder

class SettingsCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager, cls.navigation = builder.build()

    def test_candidate_compiles(self):
        compile(self.manager, "bob-manager", "exec")
        compile(self.navigation, "navigation_shell", "exec")

    def test_settings_route_present(self):
        self.assertIn(b'elif self.path == "/settings":', self.manager)

    def test_post_route_present(self):
        self.assertIn(b'if path == "/settings/password":', self.manager)

    def test_dynamic_password_verification(self):
        self.assertIn(b"dashboard_authorized(LAN_AUTH_FILE,", self.manager)

    def test_csrf_validation(self):
        self.assertIn(b'hmac.compare_digest(form["csrf"][0], TOKEN)', self.manager)

    def test_navigation_added(self):
        self.assertIn(b'("/settings", "Settings", "Settings")', self.navigation)

    def test_password_not_logged(self):
        self.assertNotIn(b'print(form', self.manager)

if __name__ == "__main__":
    unittest.main()
