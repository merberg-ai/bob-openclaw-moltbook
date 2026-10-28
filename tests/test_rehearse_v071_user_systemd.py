"""No systemd invoked by these tests. Transient staging contract tests."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stage_systemd_v071", ROOT / "scripts/rehearse_v071_user_systemd.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class StageContractTests(unittest.TestCase):
    def test_unique_synthetic_name(self):
        self.assertTrue(mod.safe_unit("bob-v071-stage-012345abcdef.service"))
    def test_real_unit_not_allowed(self):
        self.assertFalse(mod.safe_unit("bob-activity-manager.service"))
    def test_invalid_names_denied(self):
        for name in ("bob-v071-stage-.service", "bob-v071-stage-012345abcdef.timer",
                     "bob-v071-stage-012345abcdeg.service",
                     "bob-v071-stage-012345abcdef.service/evil"):
            with self.subTest(name=name):
                self.assertFalse(mod.safe_unit(name))
    def test_absent_refuses_invalid_name_before_subprocess(self):
        with patch.object(mod, "systemctl") as invoked:
            with self.assertRaises(ValueError):
                mod.absent("bob-activity-manager.service")
            invoked.assert_not_called()
    def test_existing_unit_refused(self):
        class Response:
            returncode = 0
            stdout = "LoadState=loaded\\n"
        with patch.object(mod, "systemctl", return_value=Response()):
            with self.assertRaises(ValueError):
                mod.absent("bob-v071-stage-012345abcdef.service")
    def test_unavailable_manager_refused(self):
        class Response:
            returncode = 1
            stdout = ""
        with patch.object(mod, "systemctl", return_value=Response()):
            with self.assertRaises(ValueError):
                mod.absent("bob-v071-stage-012345abcdef.service")
    def test_fixture_path_not_real_service(self):
        self.assertNotEqual(mod.LIVE_UNIT, mod.UNIT_PREFIX + "012345abcdef.service")
    def test_probe_unbound_port_false(self):
        self.assertFalse(mod.probe(0))

if __name__ == "__main__":
    unittest.main()
