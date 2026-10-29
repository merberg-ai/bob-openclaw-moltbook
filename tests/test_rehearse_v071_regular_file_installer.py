"""Disposable regular-file installation transaction tests."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("v071_regular_install", ROOT / "scripts/rehearse_v071_regular_file_installer.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class RegularFileInstallerTests(unittest.TestCase):
    def test_healthy_candidate(self):
        result = mod.exercise("healthy")
        self.assertEqual((result["outcome"], result["journal"], result["navigation_present"]),
                         ("candidate_healthy", "complete", True))

    def test_failed_health_rollback(self):
        result = mod.exercise("failed-health")
        self.assertEqual((result["outcome"], result["journal"], result["navigation_present"]),
                         ("baseline_restored", "complete", False))

    def test_crash_after_nav_recovers(self):
        self.assertEqual(mod.exercise("crash-navigation")["outcome"], "baseline_restored")

    def test_crash_after_manager_recovers(self):
        self.assertEqual(mod.exercise("crash-manager")["outcome"], "baseline_restored")

    def test_refuse_unknown_scenario(self):
        with self.assertRaises(ValueError):
            mod.exercise("production")

    def test_refuse_recovery_without_journal(self):
        root, temp = mod.stage()
        try:
            with self.assertRaises(ValueError):
                mod.recover(root)
        finally:
            temp.cleanup()

    def test_refuse_installed_drift(self):
        root, temp = mod.stage()
        try:
            manager, nav = mod.files(root)
            manager.write_text("modified")
            with self.assertRaises(ValueError):
                mod.install(root)
        finally:
            temp.cleanup()

    def test_refuse_changed_candidate_on_recovery(self):
        root, temp = mod.stage()
        try:
            mod.install(root)
            manager, nav = mod.files(root)
            manager.write_text("tampered")
            with self.assertRaises(ValueError):
                mod.recover(root)
        finally:
            temp.cleanup()

if __name__ == "__main__":
    unittest.main()
