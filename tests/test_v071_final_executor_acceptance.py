"""Final acceptance of EXACT production installer functions, wholly sandboxed.

No systemd/network/production paths: monkeypatches actual module globals and
substitutes deterministic restart/health outcomes. Run as ordinary unittest.
"""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "v071_real_executor_acceptance", ROOT / "scripts/deploy_v071_activity_manager.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class SandboxExecutor(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bob-v071-final-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        state = root / "state"
        bin_dir = root / "bin"
        bin_dir.mkdir(mode=0o700)
        manager = bin_dir / "bob-activity-manager"
        manager.write_bytes(mod.builder.SOURCE.read_bytes())
        manager.chmod(0o700)
        for key, value in (("STATE", state), ("MANAGER", manager),
                           ("NAV", bin_dir / "navigation_shell.py"),
                           ("JOURNAL", state / "transaction.json"),
                           ("PENDING", state / ".transaction-pending")):
            p = patch.object(mod, key, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(mod.planner, "plan", return_value={
            "ready_for_separate_deployment_review": True})
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(mod, "authenticate", return_value="synthetic-authorization")
        p.start()
        self.addCleanup(p.stop)
        self.root = root
        self.manager = manager
        self.nav = bin_dir / "navigation_shell.py"

    def fake_service(self, effects=None):
        calls = []
        effects = effects or {}
        def restart(action):
            self.assertEqual(action, "restart")
            calls.append(action)
            if len(calls) in effects:
                raise RuntimeError("fixture restart failure")
        return calls, restart

    def test_candidate_success(self):
        calls, restart = self.fake_service()
        with patch.object(mod, "service", side_effect=restart), patch.object(
                mod, "bounded_probe", return_value=True):
            self.assertEqual(mod.install(self.root / "fake-backup"), "candidate_healthy")
        self.assertEqual(len(calls), 1)
        self.assertEqual(mod.read_journal()["phase"], "complete")
        self.assertEqual(mod.sha(self.manager), mod.builder.sha256(mod.builder.build()[0]))
        self.assertTrue(self.nav.is_file())

    def test_failed_health_restores_original(self):
        calls, restart = self.fake_service()
        checks = iter((True, False, True))
        with patch.object(mod, "service", side_effect=restart), patch.object(
                mod, "bounded_probe", side_effect=lambda *a, **k: next(checks)):
            self.assertEqual(mod.install(self.root / "fake-backup"), "rolled_back")
        self.assertEqual(len(calls), 2)
        self.assertEqual(mod.sha(self.manager), mod.BASE)
        self.assertFalse(self.nav.exists())

    def test_failed_recovery_records_incident(self):
        calls, restart = self.fake_service({2: True})
        checks = iter((True, False))
        with patch.object(mod, "service", side_effect=restart), patch.object(
                mod, "bounded_probe", side_effect=lambda *a, **k: next(checks)):
            with self.assertRaises(RuntimeError):
                mod.install(self.root / "fake-backup")
        self.assertEqual(mod.read_journal()["phase"], "incident")
        self.assertEqual(mod.sha(self.manager), mod.BASE)
        self.assertFalse(self.nav.exists())

    def test_interrupted_manager_write_recovered(self):
        candidate, navigation = mod.builder.build()
        mod.secure_dir(mod.STATE)
        mod.save_once(mod.STATE / "baseline-manager", mod.builder.SOURCE.read_bytes(), 0o600)
        mod.save_once(mod.STATE / "candidate-manager", candidate, 0o600)
        mod.save_once(mod.STATE / "candidate-navigation", navigation, 0o600)
        mod.write_journal("prepared")
        mod.lab.replace_file(self.nav, navigation, None, 0o600)
        mod.lab.replace_file(self.manager, candidate, mod.BASE, 0o700)
        calls, restart = self.fake_service()
        with patch.object(mod, "service", side_effect=restart), patch.object(
                mod, "bounded_probe", return_value=True):
            self.assertEqual(mod.recover_interrupted(), "baseline_recovered")
        self.assertEqual(mod.sha(self.manager), mod.BASE)
        self.assertFalse(self.nav.exists())
        self.assertEqual(mod.read_journal()["phase"], "complete")

    def test_unexpected_manager_bytes_refused(self):
        self.manager.write_text("unreviewed change")
        with patch.object(mod, "service") as service:
            with self.assertRaises(ValueError):
                mod.install(self.root / "fake-backup")
            service.assert_not_called()

    def test_no_journal_refuses_recovery(self):
        with patch.object(mod, "service") as service:
            with self.assertRaises(ValueError):
                mod.recover_interrupted()
            service.assert_not_called()


if __name__ == "__main__":
    unittest.main()
