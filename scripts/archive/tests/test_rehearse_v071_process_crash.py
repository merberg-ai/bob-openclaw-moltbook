"""Crash-lab coverage. Child SIGKILL only inside disposable temporary fixtures."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "v071_process_crash", ROOT / "scripts/rehearse_v071_process_crash.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class ProcessCrashTests(unittest.TestCase):
    def test_pre_switch_crash(self):
        result = mod.run("prepared")
        self.assertEqual(result["selected_release"], "baseline")
        self.assertEqual(result["journal_phase"], "prepared")
        self.assertTrue(result["lock_released"])

    def test_post_switch_crash(self):
        result = mod.run("candidate_selected")
        self.assertEqual(result["selected_release"], "candidate")
        self.assertEqual(result["journal_phase"], "candidate_selected")
        self.assertTrue(result["child_killed"])

    def test_incomplete_state_refused(self):
        for checkpoint in mod.CHECKPOINTS:
            with self.subTest(checkpoint=checkpoint):
                self.assertTrue(mod.run(checkpoint)["new_transaction_refused"])

    def test_synthetic_db_intact(self):
        for checkpoint in mod.CHECKPOINTS:
            with self.subTest(checkpoint=checkpoint):
                self.assertTrue(mod.run(checkpoint)["synthetic_database_intact"])

    def test_unrecognized_checkpoint_refused(self):
        with self.assertRaises(ValueError):
            mod.run("production")

if __name__ == "__main__":
    unittest.main()
