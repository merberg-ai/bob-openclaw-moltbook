"""Durable disposable release crash/rollback tests. No production service."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "durable_disposable", ROOT / "scripts/rehearse_v071_durable_release.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class DurableReleaseTests(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(mod.scenario("healthy")["active"], "candidate")

    def test_failed_health_rolls_back(self):
        self.assertEqual(mod.scenario("failed-health")["outcome"], "rolled_back")

    def test_interrupted_prepared_recovers(self):
        self.assertEqual(mod.scenario("crash-prepared")["active"], "baseline")

    def test_interrupted_selected_recovers(self):
        self.assertEqual(mod.scenario("crash-selected")["active"], "baseline")

    def test_interrupted_restart_preserves_new_writes(self):
        result = mod.scenario("crash-restart")
        self.assertTrue(result["sqlite_preserved"])
        self.assertEqual(result["outcome"], "baseline_pointer_recovered")

    def test_refuse_unrecognized_scenario(self):
        with self.assertRaises(ValueError):
            mod.scenario("production")

    def test_refuse_missing_journal(self):
        manager, nav = mod.builder.build()
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as folder:
            root = Path(folder)
            mod.make_stage(root, mod.builder.SOURCE.read_bytes(), manager, nav)
            mod.switch(root, "baseline")
            with self.assertRaises(ValueError):
                mod.recover(root)

    def test_recovery_not_repeatable_after_complete(self):
        manager, nav = mod.builder.build()
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as folder:
            root = Path(folder)
            mod.make_stage(root, mod.builder.SOURCE.read_bytes(), manager, nav)
            mod.switch(root, "baseline")
            self.assertEqual(mod.begin(root, crash_at="candidate_selected"), "interrupted")
            mod.recover(root)
            with self.assertRaises(ValueError):
                mod.recover(root)


if __name__ == "__main__":
    unittest.main()
