"""Synthetic v0.7.1 updater state machine tests. No real services."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("plan_v071_update", ROOT / "scripts/plan_v071_update.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class PlannerTests(unittest.TestCase):
    def test_success_keeps_candidate(self):
        result = mod.simulate(candidate_healthy=True)
        self.assertTrue(result.success)
        self.assertFalse(result.restored)
        self.assertEqual(result.reason, "candidate_healthy")
        self.assertEqual(result.phases[-1], "complete")

    def test_failed_health_restores_baseline(self):
        result = mod.simulate(candidate_healthy=False)
        self.assertFalse(result.success)
        self.assertTrue(result.restored)
        self.assertEqual(result.reason, "rolled_back")
        self.assertIn("rollback_selected", result.phases)

    def test_failed_recovery_is_not_claimed_healthy(self):
        result = mod.simulate(candidate_healthy=False, recovery_healthy=False)
        self.assertFalse(result.success)
        self.assertFalse(result.restored)
        self.assertEqual(result.reason, "recovery_failed")
        self.assertEqual(result.phases[-1], "failed")

    def test_pre_switch_refuses_without_selecting_candidate(self):
        result = mod.simulate(candidate_healthy=True, fail_at="pre_switch")
        self.assertFalse(result.success)
        self.assertTrue(result.restored)
        self.assertNotIn("candidate_selected", result.phases)

    def test_restart_failure_restores_code(self):
        result = mod.simulate(candidate_healthy=True, fail_at="restart")
        self.assertFalse(result.success)
        self.assertTrue(result.restored)
        self.assertEqual(result.reason, "rolled_back")


if __name__ == "__main__":
    unittest.main()
