"""Consolidated release gate tests: no live network or service operations."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("v071_gate", ROOT / "scripts/v071_release_gate.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class ReleaseGateTests(unittest.TestCase):
    def test_invalid_port_refused(self):
        with self.assertRaises(ValueError):
            mod.verify_http(0)

    def test_invalid_credentials_refused(self):
        with self.assertRaises(ValueError):
            mod.verify_http(18790, {"username": "user"})

    def test_no_live_install_function(self):
        self.assertFalse(hasattr(mod, "deploy"))
        self.assertFalse(hasattr(mod, "restart"))

    def test_preflight_fail_stops_before_http(self):
        with patch.object(mod.planner, "plan", return_value={
            "ready_for_separate_deployment_review": False
        }), patch.object(mod, "verify_http") as probe:
            result = mod.run(Path("/unused"), execute_tests=False)
            self.assertFalse(result["preflight"])
            probe.assert_not_called()

if __name__ == "__main__":
    unittest.main()
