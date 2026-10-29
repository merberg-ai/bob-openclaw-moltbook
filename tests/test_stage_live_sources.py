"""Synthetic tests for SHA-pinned, private live-source staging."""

import hashlib
import json
from pathlib import Path
import stat
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stage_live_sources as stage


class SourceEscrowTests(unittest.TestCase):
    def fixture(self, tmp, text="print('hello bob')\n"):
        home = Path(tmp) / "home"
        scripts = home / ".local/bin"
        scripts.mkdir(parents=True)
        source = scripts / "bobctl"
        source.write_text(text)
        report = {
            "report_version": 1,
            "created_utc": "2026-10-28T12:11:58Z",
            "code_files": [{
                "path": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "size_bytes": source.stat().st_size,
            }],
            "unit_files": [{
                "path": "/home/operator/.config/systemd/user/openclaw-gateway.service",
                "secret": "must-not-package",
            }],
        }
        inventory = Path(tmp) / "inventory.json"
        inventory.write_text(json.dumps(report))
        return home, source, inventory

    def test_exact_source_archive_is_private_without_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, source, inventory = self.fixture(tmp)
            out = Path(tmp) / "staging"
            result = stage.stage_sources(inventory, home, out)
            self.assertEqual(result["files"], 1)
            self.assertEqual(result["secret_indicators"], 0)
            self.assertTrue(result["needs_manual_review"])
            self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
            bundle = Path(result["path"])
            self.assertEqual(stat.S_IMODE(bundle.stat().st_mode), 0o600)
            with tarfile.open(bundle, "r:gz") as tar:
                self.assertEqual(
                    sorted(tar.getnames()),
                    ["PRIVATE-SOURCE-MANIFEST.json", "bin/bobctl"]
                )
                self.assertEqual(tar.extractfile("bin/bobctl").read(), source.read_bytes())
                meta = json.load(tar.extractfile("PRIVATE-SOURCE-MANIFEST.json"))
                self.assertEqual(meta["total_bytes"], len(source.read_bytes()))
                self.assertNotIn("must-not-package", json.dumps(meta))

    def test_detects_literal_secret_without_reporting_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            example = 'token = "FAKE_TEST_SECRET_123456789"\n'
            home, _, inventory = self.fixture(tmp, text=example)
            result = stage.stage_sources(inventory, home, Path(tmp) / "staging")
            self.assertGreater(result["secret_indicators"], 0)
            self.assertNotIn("FAKE_TEST_SECRET_123456789", json.dumps(result))

    def test_refuses_hash_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, source, inventory = self.fixture(tmp)
            source.write_text("changed after inventory")
            with self.assertRaises(RuntimeError):
                stage.stage_sources(inventory, home, Path(tmp) / "staging")
            self.assertFalse((Path(tmp) / "staging").exists())

    def test_refuses_nonprivate_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, _, inventory = self.fixture(tmp)
            output = Path(tmp) / "staging"
            output.mkdir(mode=0o755)
            output.chmod(0o755)
            with self.assertRaises(PermissionError):
                stage.stage_sources(inventory, home, output)
            self.assertEqual(list(output.iterdir()), [])

    def test_refuses_source_symlink_and_unapproved_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, source, inventory = self.fixture(tmp)
            target = source.with_name("bob-real")
            source.rename(target)
            source.symlink_to(target)
            with self.assertRaises(ValueError):
                stage.stage_sources(inventory, home, Path(tmp) / "private")
            source.unlink()
            target.rename(source)
            report = json.loads(inventory.read_text())
            report["code_files"][0]["path"] = str(Path(tmp) / "outside" / "bobctl")
            inventory.write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                stage.stage_sources(inventory, home, Path(tmp) / "private")


if __name__ == "__main__":
    unittest.main()
