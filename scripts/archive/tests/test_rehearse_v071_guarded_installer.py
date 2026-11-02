"""Guarded installer sandbox regression. No real systemd or production data."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("guarded_v071", ROOT / "scripts/rehearse_v071_guarded_installer.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class GuardedInstallerTests(unittest.TestCase):
    def test_success(self):
        result = mod.run_sandbox("success")
        self.assertEqual((result["outcome"], result["release"], result["starts"]),
                         ("candidate_healthy", "candidate", 1))

    def test_failed_health_rollback(self):
        result = mod.run_sandbox("health-failure")
        self.assertEqual((result["outcome"], result["release"], result["journal"]),
                         ("rolled_back", "baseline", "complete"))

    def test_failed_recovery_incident(self):
        result = mod.run_sandbox("recovery-failure")
        self.assertEqual((result["outcome"], result["release"], result["journal"]),
                         ("recovery_failed", "baseline", "incident"))

    def test_drift_refuses_before_switch(self):
        result = mod.run_sandbox("refuse-drift")
        self.assertEqual((result["outcome"], result["starts"], result["journal"]),
                         ("preflight_refused", 0, "none"))

    def test_no_live_mode(self):
        self.assertEqual(set(mod.SCENARIOS),
                         {"success", "health-failure", "recovery-failure", "refuse-drift"})

    def test_synthetic_database_preserved(self):
        for scenario in mod.SCENARIOS:
            with self.subTest(scenario=scenario):
                self.assertTrue(mod.run_sandbox(scenario)["db_preserved"])

if __name__ == "__main__":
    unittest.main()
