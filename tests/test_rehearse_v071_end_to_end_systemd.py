"""Integrated disposable systemd runner contract tests; no systemd called."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "v071_e2e", ROOT / "scripts/rehearse_v071_end_to_end_systemd.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class EndToEndContracts(unittest.TestCase):
    def test_scenarios_limited(self):
        self.assertEqual(mod.SCENARIOS, ("healthy", "failed-health", "restart-failure"))
    def test_live_unit_never_safe(self):
        self.assertFalse(mod.units.safe_unit("bob-activity-manager.service"))
    def test_refuse_unknown_scenario_without_side_effects(self):
        with patch.object(mod.installer, "stage") as staged:
            with self.assertRaises(ValueError):
                mod.run("production")
            staged.assert_not_called()
    def test_refuse_live_stop(self):
        with patch.object(mod.units, "systemctl") as ctl:
            with self.assertRaises(ValueError):
                mod.stop("bob-activity-manager.service")
            ctl.assert_not_called()
    def test_refuse_live_start(self):
        with patch.object(mod.units, "absent") as absent:
            with self.assertRaises(ValueError):
                mod.start(Path("/tmp"), "baseline", "bob-activity-manager.service")
            absent.assert_not_called()
    def test_missing_probe_port(self):
        root, tmp = mod.installer.stage()
        try:
            self.assertFalse(mod.probe(root, "baseline"))
        finally:
            tmp.cleanup()

if __name__ == "__main__":
    unittest.main()
