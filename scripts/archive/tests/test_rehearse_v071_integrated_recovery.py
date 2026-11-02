"""Integrated offline recovery tests: real loopback HTTP and fake release/SQLite."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "v071_integrated_recovery", ROOT / "scripts/rehearse_v071_integrated_recovery.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class IntegratedRecoveryTests(unittest.TestCase):
    def test_healthy_stays_candidate(self):
        result = mod.exercise("healthy")
        self.assertEqual((result["outcome"], result["active_release"], result["http_starts"]),
                         ("candidate_healthy", "candidate", 1))

    def test_health_failure_restores_baseline(self):
        result = mod.exercise("failed-health")
        self.assertEqual((result["outcome"], result["active_release"], result["http_starts"]),
                         ("rolled_back", "baseline", 2))

    def test_recovery_failure_reports_incident(self):
        result = mod.exercise("failed-recovery")
        self.assertEqual((result["outcome"], result["journal_phase"]),
                         ("recovery_failed", "incident"))
        self.assertEqual(result["active_release"], "baseline")

    def test_interrupted_after_switch_is_not_auto_resumed(self):
        result = mod.exercise("interrupt-after-switch")
        self.assertEqual(result["outcome"], "interrupted")
        self.assertEqual(result["journal_phase"], "candidate_selected")
        self.assertEqual(result["http_starts"], 0)

    def test_interrupted_before_switch_preserves_baseline(self):
        result = mod.exercise("interrupt-before-switch")
        self.assertEqual(result["active_release"], "baseline")
        self.assertEqual(result["journal_phase"], "prepared")
        self.assertEqual(result["http_starts"], 0)

    def test_reject_unknown_scenario(self):
        with self.assertRaises(ValueError):
            mod.exercise("production")

    def test_synthetic_db_survives_every_outcome(self):
        for scenario in mod.SCENARIOS:
            with self.subTest(scenario=scenario):
                self.assertTrue(mod.exercise(scenario)["synthetic_db_preserved"])


if __name__ == "__main__":
    unittest.main()
