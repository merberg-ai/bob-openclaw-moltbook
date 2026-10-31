"""CH-HTTPS2 owner-only private certificate provisioning, disposable fixtures.

No live user config, Windows trust, Moltbook/API or dashboard modified.
Test TLS only on temporary 127.0.0.1 ephemeral sockets with fresh keys.
"""
from __future__ import annotations
from pathlib import Path
import ssl
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import prepare_ch_https2 as cert


class CHHTTPS2Tests(unittest.TestCase):
    def setUp(self):
        if not cert.OPENSSL.exists():
            self.skipTest("fixed /usr/bin/openssl not available")
        tmp=tempfile.TemporaryDirectory(prefix="synthetic-chhttps2-")
        self.addCleanup(tmp.cleanup)
        self.parent=Path(tmp.name)/"bob-system"
        self.parent.mkdir(mode=0o700)
        for name,obj in (("CONFIG_DIR",self.parent),
                         ("TLS_DIR",self.parent/"manager-tls")):
            p=patch.object(cert,name,obj)
            p.start()
            self.addCleanup(p.stop)
        for name in ("_installed_gate","_owner_boundary"):
            p=patch.object(cert,name,return_value=True)
            p.start()
            self.addCleanup(p.stop)

    def test_openssl_cert_chain_three_sans_and_authenticated_loopback_tls(self):
        summary=cert.apply()
        self.assertTrue(cert.TLS_DIR.exists())
        self.assertEqual(summary["public_ca_file"],str(cert.TLS_DIR/"ca.crt"))
        self.assertEqual(summary["lan_ip_san"],"192.168.1.24_verified")
        self.assertEqual(summary["disposable_loopback_tls"],"verified")
        self.assertEqual(cert.verify_current()["public_ca_sha256"],
                         summary["public_ca_sha256"])
        self.assertEqual(set(x.name for x in cert.TLS_DIR.iterdir()),
                         {"ca.key","ca.crt","server.key","server.crt"})
        self.assertFalse(bool(cert.TLS_DIR.stat().st_mode & 0o077))
        for p in cert.TLS_DIR.iterdir():
            self.assertFalse(bool(p.stat().st_mode & 0o077))
        self.assertFalse(summary["private_keys_exported"])
        self.assertEqual(cert._already_present(),"existing_do_not_overwrite")
        with self.assertRaisesRegex(ValueError,"preflight_not_eligible"):
            cert.apply()

    def test_symlink_or_world_readable_key_refuses(self):
        cert.apply()
        key=cert.TLS_DIR/"server.key"
        key.chmod(0o644)
        with self.assertRaisesRegex(ValueError,"private_file"):
            cert.verify_material(cert.TLS_DIR)
        key.chmod(0o600)
        target=cert.TLS_DIR/"alternate.key"
        key.rename(target)
        key.symlink_to(target)
        with self.assertRaisesRegex(ValueError,"private_file"):
            cert.verify_material(cert.TLS_DIR)

    def test_wrong_public_key_fails_verified_leaf(self):
        cert.apply()
        path=cert.TLS_DIR/"server.key"
        path.write_bytes((cert.TLS_DIR/"ca.key").read_bytes())
        with self.assertRaises((ValueError,ssl.SSLError)):
            cert.verify_material(cert.TLS_DIR)

    def test_failed_generation_cleans_private_stage_without_install(self):
        with patch.object(cert,"_generate",side_effect=ValueError("mock failure")):
            with self.assertRaisesRegex(ValueError,"mock failure"):
                cert.apply()
        self.assertFalse(cert.TLS_DIR.exists())
        self.assertEqual(list(self.parent.iterdir()),[])

    def test_existing_dir_or_symlink_refuses_no_overwrite(self):
        cert.TLS_DIR.mkdir(mode=0o700)
        (cert.TLS_DIR/"ca.key").write_text("private from old owner")
        self.assertEqual(cert._already_present(),"existing_do_not_overwrite")
        with self.assertRaises(ValueError):
            cert.apply()
        self.assertEqual((cert.TLS_DIR/"ca.key").read_text(),
                         "private from old owner")
        (cert.TLS_DIR/"ca.key").unlink()
        cert.TLS_DIR.rmdir()
        cert.TLS_DIR.symlink_to(self.parent)
        self.assertEqual(cert._already_present(),"untrusted")
        with self.assertRaises(ValueError):
            cert.apply()

    def test_default_cli_is_readonly_and_apply_needs_tty_confirmation(self):
        with patch.object(cert,"apply") as apply,patch.object(
                cert.sys,"stdin") as stdin,patch.object(
                cert.os,"geteuid",return_value=1000):
            stdin.isatty.return_value=False
            self.assertEqual(cert.main([]),0)
            self.assertEqual(cert.main(["--json"]),0)
            self.assertEqual(cert.main(["--apply"]),1)
            self.assertEqual(cert.main(["--import-windows"]),2)
            apply.assert_not_called()
        self.assertEqual(cert._already_present(),"absent")


if __name__=="__main__":
    unittest.main()
