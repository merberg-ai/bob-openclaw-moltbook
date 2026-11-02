"""Offline regression tests for redacted systemd configuration classification."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / "scripts/inspect_v071_effective_unit.py"
spec = importlib.util.spec_from_file_location("inspect_v071_effective_unit", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EffectiveUnitTests(unittest.TestCase):
    def fixture(self):
        return {k: "" for k in module.PROPS} | {
            "LoadState": "loaded", "ActiveState": "active", "SubState": "running",
            "ExecStart": "argv[]=/usr/bin/python3 /home/test/.local/bin/bob-activity-manager",
            "DropInPaths": "/private/override.conf",
        }

    def test_direct_entrypoint_and_private_metadata_flags(self):
        data = self.fixture()
        data["EnvironmentFiles"] = "/secret/file"
        data["WorkingDirectory"] = "/secret/cwd"
        data["ExecStartPre"] = "/secret/hook"
        status = module.classify(data, Path("/home/test/.local/bin/bob-activity-manager"))
        self.assertTrue(status["direct_manager_reference"])
        self.assertTrue(status["environment_files_declared"])
        self.assertTrue(status["custom_working_directory"])
        self.assertTrue(status["pre_post_or_condition_hooks"])
        self.assertNotIn("/secret", repr(status))

    def test_false_positive_manager_suffix_refused(self):
        data = self.fixture()
        data["ExecStart"] += "-old"
        self.assertFalse(module.classify(data, Path("/home/test/.local/bin/bob-activity-manager"))["direct_manager_reference"])

    def test_reject_malformed_response(self):
        class Result:
            returncode = 0
            stdout = "LoadState=loaded\nExecStart=secret\n"
        with patch.object(module.subprocess, "run", return_value=Result()):
            with self.assertRaises(ValueError):
                module.inspect()

    def test_full_mocked_response_does_not_leak_secrets(self):
        vals = self.fixture()
        vals["Environment"] = "API_KEY=secret"
        class Result:
            returncode = 0
            stdout = "\n".join(f"{k}={v}" for k, v in vals.items()) + "\n"
        with patch.object(module.subprocess, "run", return_value=Result()):
            status, omitted = module.inspect()
        self.assertEqual(omitted, [])
        self.assertTrue(status["inline_environment_declared"])
        self.assertNotIn("secret", repr(status))

    def test_omitted_optional_systemd_properties_are_reported(self):
        vals = self.fixture()
        vals.pop("RootImage")
        vals.pop("EnvironmentFiles")
        class Result:
            returncode = 0
            stdout = "\n".join(f"{k}={v}" for k, v in vals.items()) + "\n"
        with patch.object(module.subprocess, "run", return_value=Result()):
            status, omitted = module.inspect()
        self.assertIn("RootImage", omitted)
        self.assertIn("EnvironmentFiles", omitted)
        self.assertTrue(status["service_running"])


if __name__ == "__main__":
    unittest.main()
