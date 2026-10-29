import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/lib/bob"))
import bob_dashboard_auth as auth

class RotationTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.root.chmod(0o700)
        self.path = self.root / "lan-auth.json"
        self.old = "old-private-password-123"
        self.new = "new-private-password-456"
        self.path.write_text(json.dumps({"username": "bob", "password": self.old}))
        self.path.chmod(0o600)

    def header(self, password):
        return "Basic " + base64.b64encode(("bob:" + password).encode()).decode()

    def test_auth_live_after_rotation(self):
        self.assertTrue(auth.authorized(self.path, self.header(self.old)))
        auth.rotate(self.path, self.old, self.new, self.new)
        self.assertFalse(auth.authorized(self.path, self.header(self.old)))
        self.assertTrue(auth.authorized(self.path, self.header(self.new)))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_reject_wrong_current(self):
        with self.assertRaises(auth.CredentialError):
            auth.rotate(self.path, "incorrect", self.new, self.new)
        self.assertTrue(auth.authorized(self.path, self.header(self.old)))

    def test_reject_mismatch(self):
        with self.assertRaises(auth.CredentialError):
            auth.rotate(self.path, self.old, self.new, "mismatch")

    def test_reject_short_new_password(self):
        with self.assertRaises(auth.CredentialError):
            auth.rotate(self.path, self.old, "short", "short")

    def test_reject_control_characters(self):
        bad = self.new + "\n"
        with self.assertRaises(auth.CredentialError):
            auth.rotate(self.path, self.old, bad, bad)

    def test_fail_closed_missing(self):
        self.path.unlink()
        self.assertFalse(auth.authorized(self.path, self.header(self.old)))

    def test_fail_closed_world_readable(self):
        self.path.chmod(0o644)
        self.assertFalse(auth.authorized(self.path, self.header(self.old)))
        with self.assertRaises(auth.CredentialError):
            auth.rotate(self.path, self.old, self.new, self.new)

    def test_fail_closed_symlink(self):
        other = self.root / "other"
        self.path.rename(other)
        self.path.symlink_to(other)
        self.assertFalse(auth.authorized(self.path, self.header(self.old)))

    def test_reject_reuse_password(self):
        with self.assertRaises(auth.CredentialError):
            auth.rotate(self.path, self.old, self.old, self.old)

if __name__ == "__main__":
    unittest.main()
