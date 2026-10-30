"""R2 versioned shadow installation and legacy dashboard bridge, offline only."""
from __future__ import annotations

from pathlib import Path
import ast
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in ("src", "src/lib/bob", "scripts"):
    sys.path.insert(0, str(ROOT / path))
import bob_v08.install as inst
import bob_v08.evidence as evidence
import build_v08_shadow_package as archive_builder
import build_v08_shadow_dashboard as page_builder
import build_v076_fm41_candidate as prior


def post_functions(code: bytes):
    tree = ast.parse(code)
    return [ast.dump(node, include_attributes=False) for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in ("do_POST", "do_PUT", "do_DELETE")]


class ShadowActivationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name) / "openclaw"
        home.mkdir(mode=0o700)
        paths = {
            "HOME": home,
            "BIN": home / ".local/bin",
            "UPDATER_LOCK": home / ".local/state/bob-updater/lock",
            "REGISTRY": home / ".local/state/bob-updater/installed.json",
            "STATE": home / ".local/state/bob-v08-activation",
            "JOURNAL": home / ".local/state/bob-v08-activation/journal.json",
            "LOCK": home / ".local/state/bob-v08-activation/lock",
            "STORE": home / ".local/share/bob",
            "RELEASE_DIR": home / ".local/share/bob/releases/v0.8.0-shadow1",
            "ARCHIVE": home / ".local/share/bob/releases/v0.8.0-shadow1/bob_v08_package.pyz",
            "POINTER": home / ".local/share/bob/current.json",
            "UNITS": home / ".config/systemd/user"
        }
        for key, value in paths.items():
            p = patch.object(inst, key, value)
            p.start()
            self.addCleanup(p.stop)
        self.calls = []
        def fake_systemctl(*args):
            self.calls.append(args)
        p = patch.object(inst, "systemctl", fake_systemctl)
        p.start()
        self.addCleanup(p.stop)
        inst.BIN.mkdir(mode=0o700, parents=True)
        inst.UPDATER_LOCK.parent.mkdir(mode=0o700, parents=True)
        self.bundle, launcher = archive_builder.build()
        (inst.BIN / inst.BUNDLE_NAME).write_bytes(self.bundle)
        (inst.BIN / "bob-v08-shadow").write_bytes(launcher)
        (inst.BIN / "bob-v08-activate").write_text("reviewed CLI")
        reg = {
            "format": "bob-updater-v1", "release": inst.RELEASE,
            "files": {
                inst.BUNDLE_NAME: hashlib.sha256(self.bundle).hexdigest(),
                "bob-v08-shadow": "a" * 64,
                "bob-v08-activate": "b" * 64}}
        inst.REGISTRY.write_text(json.dumps(reg))
        inst.REGISTRY.chmod(0o600)

    def test_versioned_copy_pointer_and_local_user_timer_are_reversible(self):
        self.assertEqual(inst.status()["installed"], "not_activated")
        self.assertEqual(inst.activate(), "active")
        self.assertEqual(inst.read_phase()["phase"], "active")
        self.assertEqual(inst.ARCHIVE.read_bytes(), self.bundle)
        self.assertEqual(json.loads(inst.POINTER.read_text()),
                         {"release": inst.RELEASE,
                          "sha256": hashlib.sha256(self.bundle).hexdigest()})
        self.assertIn(("enable", "--now", inst.TIMER), self.calls)
        self.assertIn(("is-active", inst.TIMER), self.calls)
        self.assertIn("NoNewPrivileges=true",
                      (inst.UNITS / inst.SERVICE).read_text())
        self.assertIn("OnUnitInactiveSec=20min",
                      (inst.UNITS / inst.TIMER).read_text())
        self.assertEqual(inst.deactivate(), "inactive")
        self.assertFalse(inst.POINTER.exists())
        self.assertFalse(inst.ARCHIVE.exists())
        self.assertFalse((inst.UNITS / inst.TIMER).exists())
        self.assertEqual(inst.activate(), "active")
        self.assertEqual(inst.status()["installed"], "active")

    def test_registry_chain_or_package_drift_blocks_any_activation(self):
        with inst.REGISTRY.open() as stream:
            record = json.load(stream)
        record["release"] = "v0.7.8-updater2"
        inst.REGISTRY.write_text(json.dumps(record))
        inst.REGISTRY.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "unexpected_installed_release"):
            inst.activate()
        self.assertFalse(inst.JOURNAL.exists())
        record["release"] = inst.RELEASE
        inst.REGISTRY.write_text(json.dumps(record))
        with (inst.BIN / inst.BUNDLE_NAME).open("ab") as stream:
            stream.write(b"drift")
        with self.assertRaisesRegex(ValueError, "installed_bundle_hash_drift"):
            inst.activate()
        self.assertFalse(inst.JOURNAL.exists())

    def test_modified_user_unit_blocks_deletion(self):
        self.assertEqual(inst.activate(), "active")
        unit = inst.UNITS / inst.TIMER
        unit.write_text(unit.read_text() + "\n# unexpected override")
        with self.assertRaisesRegex(ValueError, "shadow_service_file_modified"):
            inst.deactivate()
        self.assertTrue(unit.exists())
        self.assertTrue(inst.POINTER.exists())

    def test_activation_enable_failure_rolls_back_staged_files(self):
        def fail_enabling(*args):
            self.calls.append(args)
            if args[:2] == ("enable", "--now"):
                raise RuntimeError("synthetic failure")
        with patch.object(inst, "systemctl", fail_enabling):
            self.assertEqual(inst.activate(), "rolled_back")
        self.assertEqual(inst.read_phase()["phase"], "inactive")
        self.assertFalse(inst.POINTER.exists())
        self.assertFalse(inst.ARCHIVE.exists())
        self.assertFalse((inst.UNITS / inst.TIMER).exists())

    def test_activation_will_not_overwrite_existing_unauthorized_timer(self):
        inst.UNITS.mkdir(mode=0o700, parents=True)
        existing = inst.UNITS / inst.TIMER
        existing.write_text("[Unit]\nOther agent")
        with self.assertRaisesRegex(ValueError, "activation_conflicts"):
            inst.activate()
        self.assertIn("Other agent", existing.read_text())
        self.assertFalse(inst.JOURNAL.exists())

    def test_no_remote_posting_or_root_units_in_activation(self):
        src = (ROOT / "src/bob_v08/install.py").read_text()
        self.assertNotIn("urllib.request", src)
        self.assertNotIn("moltbook.com", src)
        self.assertNotIn("api_key", src)
        self.assertNotIn("sudo", src)
        for unit in inst.units().values():
            self.assertNotIn(b"publisher", unit.lower())
            self.assertIn(b"shadow", unit.lower())


class AuthenticatedBridgeContracts(unittest.TestCase):
    def test_generated_routes_are_get_only_and_preserve_post_ast(self):
        before, before_nav = prior.build()
        after, nav = page_builder.build()
        self.assertEqual(post_functions(before), post_functions(after))
        self.assertEqual(after.count(b'"/v08/now"'), 1)
        self.assertEqual(after.count(b'"/v08/inbox"'), 1)
        self.assertIn(b"bob_v08_bridge", after)
        self.assertNotIn(b'"/v08/now"', before)
        self.assertIn(b'("/v08/now", "Bob v0.8', nav)
        self.assertIn(b'("/v08/inbox", "Bob v0.8', nav)
        self.assertIn(b'("/moltbook/social-memory"', nav)
        self.assertNotEqual(nav, before_nav)

    def test_model_never_calls_credentials_or_publisher(self):
        for path in (ROOT / "src/bob_v08/shadow.py",
                     ROOT / "src/bob_v08/install.py",
                     ROOT / "src/lib/bob/bob_v08_bridge.py"):
            source = path.read_text()
            self.assertNotIn("api_key(", source)
            self.assertNotIn("bob-moltbook-publisher", source)
            self.assertNotIn("MOLTBOOK_API", source)


if __name__ == "__main__":
    unittest.main()
