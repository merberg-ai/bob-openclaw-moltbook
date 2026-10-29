"""Original-manager real-systemd rollback safety contract tests. No transient units."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "v071_real_baseline", ROOT / "scripts/rehearse_v071_original_manager_rollback.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class OriginalRollbackTests(unittest.TestCase):
    def test_only_known_scenarios(self):
        self.assertEqual(mod.SCENARIOS, ("healthy", "failed-health"))

    def test_unknown_scenario_denied_before_start(self):
        with patch.object(mod.units, "absent") as absent:
            with self.assertRaises(ValueError):
                mod.execute("live")
            absent.assert_not_called()

    def test_original_baseline_pinned(self):
        baseline = mod.builder.SOURCE.read_bytes()
        self.assertEqual(mod.builder.sha256(baseline),
                         mod.builder.PINNED_BASELINE_SHA256)

    def test_prepare_two_file_candidate_and_original(self):
        with tempfile.TemporaryDirectory(prefix=mod.PREFIX) as temp:
            root = mod.prepare(Path(temp))
            self.assertEqual((root / "baseline/bob-activity-manager").read_bytes(),
                             mod.builder.SOURCE.read_bytes())
            self.assertTrue((root / "bin/navigation_shell.py").is_file())
            self.assertTrue((root / "bin/bob-activity-manager").is_file())

    def test_launch_refuses_live_unit(self):
        with tempfile.TemporaryDirectory(prefix=mod.PREFIX) as temp:
            with self.assertRaises(ValueError):
                mod.launch(Path(temp), "candidate", mod.units.LIVE_UNIT)

    def test_launch_refuses_unknown_release(self):
        with tempfile.TemporaryDirectory(prefix=mod.PREFIX) as temp:
            with self.assertRaises(ValueError):
                mod.launch(Path(temp), "untrusted", "bob-v071-stage-012345abcdef.service")

if __name__ == "__main__":
    unittest.main()
