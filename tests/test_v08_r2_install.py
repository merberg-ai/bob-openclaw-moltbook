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
import bob_release_updater as updater
from unittest.mock import Mock


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
            "RELEASE_DIR": home / ".local/share/bob/releases/v0.8.0-shadow4",
            "ARCHIVE": home / ".local/share/bob/releases/v0.8.0-shadow4/bob_v08_package.pyz",
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

    def test_prior_shadow1_inactive_journal_allows_shadow2_activate(self):
        # Owner deactivates the previous version *before* applying shadow2.
        inst.STATE.mkdir(mode=0o700, parents=True)
        sha = hashlib.sha256(self.bundle).hexdigest()
        prior = {
            "format": "bob-v08-activation-v1",
            "release": "v0.8.0-shadow1",
            "phase": "inactive",
            "bundle_sha": sha
        }
        inst.JOURNAL.write_text(json.dumps(prior))
        inst.JOURNAL.chmod(0o600)
        self.assertEqual(inst.read_phase(), prior)
        self.assertEqual(inst.activate(), "active")
        self.assertEqual(inst.read_phase()["release"], inst.RELEASE)
        self.assertEqual(inst.deactivate(), "inactive")

    def test_prior_shadow2_inactive_journal_allows_shadow3_activation(self):
        inst.STATE.mkdir(mode=0o700, parents=True)
        prior = {
            "format": "bob-v08-activation-v1",
            "release": "v0.8.0-shadow2",
            "phase": "inactive",
            "bundle_sha": "a" * 64
        }
        inst.JOURNAL.write_text(json.dumps(prior))
        inst.JOURNAL.chmod(0o600)
        self.assertEqual(inst.read_phase(), prior)
        self.assertEqual(inst.activate(), "active")
        self.assertEqual(inst.read_phase()["release"], "v0.8.0-shadow3")
        self.assertEqual(inst.deactivate(), "inactive")

    def test_prior_shadow3_inactive_journal_allows_shadow4_activation(self):
        inst.STATE.mkdir(mode=0o700, parents=True)
        prior = {
            "format": "bob-v08-activation-v1",
            "release": "v0.8.0-shadow3",
            "phase": "inactive",
            "bundle_sha": "a" * 64
        }
        inst.JOURNAL.write_text(json.dumps(prior))
        inst.JOURNAL.chmod(0o600)
        self.assertEqual(inst.read_phase(), prior)
        self.assertEqual(inst.activate(), "active")
        self.assertEqual(inst.read_phase()["release"], "v0.8.0-shadow4")
        self.assertEqual(inst.deactivate(), "inactive")

    def test_prior_shadow3_active_journal_fails_closed(self):
        inst.STATE.mkdir(mode=0o700, parents=True)
        prior = {
            "format": "bob-v08-activation-v1",
            "release": "v0.8.0-shadow3",
            "phase": "active",
            "bundle_sha": "a" * 64
        }
        inst.JOURNAL.write_text(json.dumps(prior))
        inst.JOURNAL.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "invalid_activation_journal"):
            inst.activate()

    def test_prior_shadow2_active_journal_is_rejected(self):
        inst.STATE.mkdir(mode=0o700, parents=True)
        prior = {
            "format": "bob-v08-activation-v1",
            "release": "v0.8.0-shadow2",
            "phase": "active",
            "bundle_sha": "a" * 64
        }
        inst.JOURNAL.write_text(json.dumps(prior))
        inst.JOURNAL.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "invalid_activation_journal"):
            inst.activate()

    def test_old_active_shadow1_journal_must_not_be_upgraded_in_place(self):
        inst.STATE.mkdir(mode=0o700, parents=True)
        prior = {
            "format": "bob-v08-activation-v1",
            "release": "v0.8.0-shadow1",
            "phase": "active",
            "bundle_sha": "a" * 64
        }
        inst.JOURNAL.write_text(json.dumps(prior))
        inst.JOURNAL.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "invalid_activation_journal"):
            inst.activate()

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

    def test_deactivation_stop_failure_keeps_owned_units_and_incident(self):
        self.assertEqual(inst.activate(), "active")
        timer = inst.UNITS / inst.TIMER
        service = inst.UNITS / inst.SERVICE
        def fails_stop(*args):
            if args[:2] == ("disable", "--now"):
                raise RuntimeError("synthetic systemd unavailable")
            self.calls.append(args)
        with patch.object(inst, "systemctl", fails_stop):
            with self.assertRaises(RuntimeError):
                inst.deactivate()
        self.assertTrue(timer.exists())
        self.assertTrue(service.exists())
        self.assertTrue(inst.ARCHIVE.exists())
        self.assertEqual(inst.read_phase()["phase"], "incident")

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


class RollbackBoundaryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.state = self.home / "state"
        self.tx = self.state / "tx-v0.8.0-shadow1"
        self.tx.mkdir(mode=0o700, parents=True)
        previous = self.tx / "registry-before.json"
        previous.write_text(json.dumps({"release": "v0.7.8-updater2"}))
        previous.chmod(0o600)
        patches = [
            patch.object(updater, "HOME", self.home),
            patch.object(updater, "STATE_DIR", self.state),
            patch.object(updater, "read_journal",
                         return_value={"format": updater.FORMAT,
                                       "release": "v0.8.0-shadow1",
                                       "phase": "complete", "restart_manager": True}),
            patch.object(updater, "registry",
                         return_value={"format": updater.FORMAT,
                                       "release": "v0.8.0-shadow1", "files": {}}),
            patch.object(updater, "live_ok", return_value=True),
            patch.object(updater, "healthy", return_value=True),
            patch.object(updater, "rollback", return_value="baseline_restored"),
            patch.object(updater, "locked",
                         side_effect=lambda: os.open(self.home / "lock", os.O_CREAT | os.O_RDWR, 0o600))
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_exact_r1_rollback_uses_verified_archive_without_db_restore(self):
        self.assertEqual(updater.rollback_shadow_to("v0.7.8-updater2", auth="fake"),
                         "baseline_restored")
        updater.rollback.assert_called_once()
        self.assertEqual(updater.rollback.call_args.kwargs["auth"], "fake")
        with self.assertRaisesRegex(ValueError, "unsupported_rollback_target"):
            updater.rollback_shadow_to("some-old-release", auth="fake")

    def test_active_shadow_or_context_refuses_code_rollback(self):
        state = self.home / ".local/state/bob-v08-activation"
        state.mkdir(parents=True)
        (state / "journal.json").write_text(json.dumps({"phase": "active"}))
        (state / "journal.json").chmod(0o600)
        with self.assertRaisesRegex(ValueError, "deactivate_shadow_before"):
            updater.rollback_shadow_to("v0.7.8-updater2", auth="fake")
        (state / "journal.json").write_text(json.dumps({"phase": "inactive"}))
        context = self.home / ".local/state/bob-v08-context"
        context.mkdir(parents=True)
        (context / "enabled.json").write_text(json.dumps({"enabled": True}))
        (context / "enabled.json").chmod(0o600)
        with self.assertRaisesRegex(ValueError, "disable_gateway_experience_context_before"):
            updater.rollback_shadow_to("v0.7.8-updater2", auth="fake")
        self.assertEqual(updater.rollback.call_count, 0)

    def test_installed_drift_blocks_rollback(self):
        with patch.object(updater, "live_ok", return_value=False):
            with self.assertRaisesRegex(ValueError, "shadow_installed_hash_drift"):
                updater.rollback_shadow_to("v0.7.8-updater2", auth="fake")
        self.assertEqual(updater.rollback.call_count, 0)



if __name__ == "__main__":
    unittest.main()
