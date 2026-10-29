"""Production executor contracts. Never invoke --apply or change live state."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("v071_executor", ROOT / "scripts/deploy_v071_activity_manager.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class ExecutorContracts(unittest.TestCase):
    def test_confirmation_token(self):
        self.assertEqual(mod.CONFIRM, "DEPLOY-BOB-V071")
    def test_unit_name_frozen(self):
        self.assertEqual(mod.UNIT, "bob-activity-manager.service")
    def test_no_arbitrary_systemd_actions(self):
        with self.assertRaises(ValueError):
            mod.service("stop")
    def test_phases_include_incident(self):
        self.assertIn("incident", mod.STATES)
    def test_install_path_expected(self):
        self.assertEqual(mod.MANAGER.name, "bob-activity-manager")
        self.assertEqual(mod.NAV.name, "navigation_shell.py")
    def test_recovery_requires_existing_transaction(self):
        with patch.object(mod, "secure_dir"), patch.object(mod, "read_journal", return_value=None), patch.object(mod, "service") as srv, patch.object(mod.os, "open", return_value=99), patch.object(mod.os, "close"), patch.object(mod.fcntl, "flock"):
            with self.assertRaises(ValueError):
                mod.recover_interrupted()
            srv.assert_not_called()

    def test_no_unapproved_plan_install(self):
        with patch.object(mod, "install") as install:
            self.assertEqual(mod.CONFIRM, "DEPLOY-BOB-V071")
            install.assert_not_called()

if __name__ == "__main__":
    unittest.main()
