"""Synthetic coverage for the redacted service entrypoint classifier."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

file = Path(__file__).resolve().parents[1] / "scripts/inspect_v071_service_entrypoint.py"
spec = importlib.util.spec_from_file_location("v071_entrypoint", file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class EntryPointTests(unittest.TestCase):
    def test_direct_match_and_wrapper_refusal(self):
        manager = Path("/home/test/.local/bin/bob-activity-manager")
        values = {
            "LoadState": "loaded", "ActiveState": "active", "SubState": "running",
            "FragmentPath": "/private/fragment", "DropInPaths": "",
            "ExecStart": "argv[]=/usr/bin/python3 /home/test/.local/bin/bob-activity-manager",
        }
        result = mod.classify(values, manager)
        self.assertTrue(result["direct_manager_reference"])
        self.assertFalse(result["service_launch_details_ambiguous"])
        values["ExecStart"] += "-old"
        self.assertFalse(mod.classify(values, manager)["direct_manager_reference"])
        values["ExecStart"] = "argv[]=/usr/local/bin/start-bob"
        self.assertTrue(mod.classify(values, manager)["service_launch_details_ambiguous"])

    def test_missing_service_details(self):
        values = {"LoadState": "not-found", "ActiveState": "inactive", "SubState": "dead"}
        result = mod.classify(values, Path("/some/manager"))
        self.assertFalse(result["service_running"])
        self.assertFalse(result["unit_fragment_declared"])
        self.assertFalse(result["direct_manager_reference"])

    def test_inspector_does_not_print_private_execstart(self):
        class Result:
            returncode = 0
            stdout = (
                "LoadState=loaded\nActiveState=active\nSubState=running\n"
                "FragmentPath=/secret/unit\nDropInPaths=\n"
                "ExecStart={ argv[]=/secret/bin --token private; }\n"
            )
        with patch.object(mod.subprocess, "run", return_value=Result()):
            status = mod.inspect()
        self.assertFalse(status["direct_manager_reference"])
        self.assertNotIn("private", repr(status))
        self.assertNotIn("/secret", repr(status))


if __name__ == "__main__":
    unittest.main()
