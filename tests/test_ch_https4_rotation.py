"""CH-HTTPS4 offline credential rotation and fail-closed gates (no live host)."""
from __future__ import annotations

import base64
import contextlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src/lib/bob"))
import bob_dashboard_auth as auth
import ch_https4_rotate_dashboard as rotation


class CHHTTPS4RotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "lan-auth.json"
        self.path.parent.chmod(0o700)
        self.old = "previous-history-password-123"
        self.new = "new-private-HTTPS-password-456"
        self.path.write_text(json.dumps({"username": "bob", "password": self.old}))
        self.path.chmod(0o600)

    def header(self, password):
        return "Basic " + base64.b64encode(
            ("bob:" + password).encode("utf-8")).decode("ascii")

    def responses(self):
        return [
            (401, b""),
            (200, b"Bob R3 Controls R3 automatic publishing compiled locked"),
            (401, b""),
        ]

    def test_accepted_rotation_requires_old_401_new_200_anon_401(self):
        with patch.object(rotation, "_ready", return_value=True), \
             patch.object(rotation, "_https_get", side_effect=self.responses()) as get:
            self.assertTrue(rotation.rotate_and_verify(
                self.path, self.old, self.new, self.new))
            self.assertEqual(get.call_count, 3)
            self.assertEqual(get.call_args_list[-1].args, (None,))
        self.assertFalse(auth.authorized(self.path, self.header(self.old)))
        self.assertTrue(auth.authorized(self.path, self.header(self.new)))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_bad_old_password_refused_without_writing(self):
        with patch.object(rotation, "_ready", return_value=True), \
             patch.object(rotation, "_https_get") as get:
            with self.assertRaises(auth.CredentialError):
                rotation.rotate_and_verify(self.path,
                    "incorrect-current-password", self.new, self.new)
            get.assert_not_called()
        self.assertTrue(auth.authorized(self.path, self.header(self.old)))

    def test_not_ready_never_rotates_or_probes(self):
        with patch.object(rotation, "_ready", return_value=False), \
             patch.object(rotation.auth, "rotate") as change, \
             patch.object(rotation, "_https_get") as get:
            with self.assertRaises(auth.CredentialError):
                rotation.rotate_and_verify(self.path,self.old,self.new,self.new)
            change.assert_not_called()
            get.assert_not_called()

    def test_reuse_non_ascii_short_and_mismatch_refused(self):
        bad = (
            (self.old, self.old),
            ("short", "short"),
            (self.new, "different"),
            ("extended-usable-but-non-ascii-é", "extended-usable-but-non-ascii-é"),
            ("X" * 257, "X" * 257),
        )
        with patch.object(rotation, "_ready", return_value=True):
            for candidate, confirm in bad:
                with self.subTest(candidate=candidate[:12]):
                    with self.assertRaises(auth.CredentialError):
                        rotation.rotate_and_verify(self.path,self.old,
                            candidate,confirm)
        self.assertTrue(auth.authorized(self.path,self.header(self.old)))

    def test_postflight_failure_never_restores_old_password(self):
        with patch.object(rotation, "_ready", return_value=True), \
             patch.object(rotation, "_https_get",
                          side_effect=[(200,b""),self.responses()[1],(401,b"")]):
            self.assertFalse(rotation.rotate_and_verify(
                self.path,self.old,self.new,self.new))
        self.assertFalse(auth.authorized(self.path,self.header(self.old)))
        self.assertTrue(auth.authorized(self.path,self.header(self.new)))

    def test_new_auth_failure_or_anonymous_success_blocks_acceptance(self):
        for values in (
            [(401,b""),(401,b""),(401,b"")],
            [(401,b""),self.responses()[1],(200,b"")],
            [(401,b""),(200,b"unrelated dashboard"),(401,b"")],
        ):
            with self.subTest(values=values), \
                 patch.object(rotation, "_https_get",side_effect=values):
                auth.rotate(self.path,self.old,self.new,self.new)
                self.assertFalse(rotation._rotation_proven(
                    self.path,"bob",self.old,self.new))
                auth.rotate(self.path,self.new,self.old,self.old)

    def test_tls_probe_failure_returns_unverified(self):
        with patch.object(rotation, "_ready", return_value=True), \
             patch.object(rotation, "_https_get",
                          side_effect=ConnectionRefusedError("offline")):
            self.assertFalse(rotation.rotate_and_verify(
                self.path,self.old,self.new,self.new))
        self.assertTrue(auth.authorized(self.path,self.header(self.new)))

    def test_preflight_is_read_only_and_apply_requires_terminal(self):
        with patch.object(rotation,"_operator_account",return_value=True), \
             patch.object(rotation,"_ready",return_value=True), \
             patch.object(rotation.auth,"rotate") as change, \
             patch.object(rotation,"_https_get") as get, \
             contextlib.redirect_stdout(StringIO()):
            self.assertEqual(rotation.main([]),0)
            self.assertEqual(rotation.main(["--verify"]),0)
            self.assertEqual(rotation.main(["--preflight"]),0)
            self.assertEqual(rotation.main(["--apply","--unsafe"]),2)
            with patch.object(sys.stdin,"isatty",return_value=False):
                self.assertEqual(rotation.main(["--apply"]),1)
            change.assert_not_called()
            get.assert_not_called()

    def test_apply_requires_explicit_phrase(self):
        with patch.object(rotation,"_operator_account",return_value=True), \
             patch.object(rotation,"_ready",return_value=True), \
             patch.object(sys.stdin,"isatty",return_value=True), \
             patch.object(sys.stderr,"isatty",return_value=True), \
             patch("builtins.input",return_value="no"), \
             patch.object(rotation.getpass,"getpass") as secret, \
             patch.object(rotation.auth,"rotate") as change, \
             contextlib.redirect_stdout(StringIO()):
            self.assertEqual(rotation.main(["--apply"]),1)
            secret.assert_not_called()
            change.assert_not_called()

    def test_error_does_not_claim_credentials_unchanged(self):
        output = StringIO()
        with patch.object(rotation,"_operator_account",return_value=True), \
             patch.object(rotation,"_ready",return_value=True), \
             patch.object(sys.stdin,"isatty",return_value=True), \
             patch.object(sys.stderr,"isatty",return_value=True), \
             patch("builtins.input",return_value=rotation.CONFIRMATION), \
             patch.object(rotation.getpass,"getpass",
                          side_effect=[self.old,self.new,self.new]), \
             patch.object(rotation,"rotate_and_verify",
                          side_effect=OSError("synthetic fsync failure")), \
             contextlib.redirect_stdout(output):
            self.assertEqual(rotation.main(["--apply"]),1)
        self.assertIn("INDETERMINATE",output.getvalue())
        self.assertNotIn(self.old,output.getvalue())
        self.assertNotIn(self.new,output.getvalue())


if __name__ == "__main__":
    unittest.main()
