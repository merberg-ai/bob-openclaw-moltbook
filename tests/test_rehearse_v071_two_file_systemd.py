"""No live systemd calls: test read-only controls and candidate health helpers."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "v071_two_file_systemd", ROOT / "scripts/rehearse_v071_two_file_systemd.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class TwoFileSystemdTests(unittest.TestCase):
    def test_scenarios_are_synthetic_only(self):
        self.assertEqual(mod.SCENARIOS, ("healthy", "failed-health"))

    def test_live_unit_never_a_stage_name(self):
        self.assertFalse(mod.units.safe_unit(mod.LIVE_UNIT))

    def test_missing_port_not_ready(self):
        self.assertIsNone(mod.port_ready(Path("/nonexistent-bob-v071-test-port")))

    def test_bad_port_value_not_accepted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "port"
            file.write_text("not-a-port")
            self.assertIsNone(mod.port_ready(file))
            file.write_text("99999")
            self.assertIsNone(mod.port_ready(file))

    def test_probe_unbound_port_fails(self):
        self.assertFalse(mod.preview_probe(0))

    def test_cleanup_refuses_live_service_name(self):
        with patch.object(mod.units, "systemctl") as runner:
            with self.assertRaises(ValueError):
                mod.stop_unit(mod.LIVE_UNIT)
            runner.assert_not_called()

    def test_execution_rejects_unknown_scenario_before_systemd(self):
        with self.assertRaises(ValueError):
            mod.execute("production")

if __name__ == "__main__":
    unittest.main()
