"""No-host effective systemd preflight classification tests."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("effective_v071", ROOT / "scripts/preflight_v071_effective_service.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
MANAGER = Path("/home/example/.local/bin/bob-activity-manager")

def fixture(**changes):
    fields = {key: "" for key in mod.KEYS}
    fields.update({
        "LoadState": "loaded", "ActiveState": "active", "SubState": "running",
        "FragmentPath": "/home/example/.config/systemd/user/bob-activity-manager.service",
        "DropInPaths": "/home/example/.config/systemd/user/bob-activity-manager.service.d/override.conf",
        "ExecStart": "{ path=" + str(MANAGER) + " ; argv[]=" + str(MANAGER)
                     + " ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }",
        "WorkingDirectory": "/home/example",
        "Environment": "SENSITIVE=REDACTED",
        "DynamicUser": "no",
    })
    fields.update(changes)
    return "".join(key + "=" + fields[key] + "\n" for key in mod.KEYS)

class EffectivePreflightTests(unittest.TestCase):
    def classify(self, raw):
        with patch.object(mod, "check_manager", return_value=True):
            return mod.classify(raw, manager=MANAGER)

    def test_expected_fixture_passes(self):
        self.assertTrue(all(self.classify(fixture()).values()))

    def test_execstart_drift_refused(self):
        self.assertFalse(self.classify(fixture(ExecStart="{ path=/bin/false ; argv[]=/bin/false ; ignore_errors=no }"))["effective_execstart_expected"])

    def test_python_interpreter_wrapper_passes(self):
        interpreter = "/usr/bin/python3"
        cmd = ("{ path=" + interpreter + " ; argv[]=" + interpreter + " " + str(MANAGER)
               + " ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }")
        self.assertTrue(self.classify(fixture(ExecStart=cmd))["effective_execstart_expected"])

    def test_python_wrapper_extra_arguments_refused(self):
        interpreter = "/usr/bin/python3"
        cmd = ("{ path=" + interpreter + " ; argv[]=" + interpreter + " -I " + str(MANAGER)
               + " ; ignore_errors=no }")
        self.assertFalse(self.classify(fixture(ExecStart=cmd))["effective_execstart_expected"])

    def test_python_wrapper_different_script_refused(self):
        interpreter = "/usr/bin/python3"
        cmd = ("{ path=" + interpreter + " ; argv[]=" + interpreter + " /tmp/untrusted.py"
               + " ; ignore_errors=no }")
        self.assertFalse(self.classify(fixture(ExecStart=cmd))["effective_execstart_expected"])

    def test_shell_wrapper_refused(self):
        cmd = "{ path=/bin/sh ; argv[]=/bin/sh " + str(MANAGER) + " ; ignore_errors=no }"
        self.assertFalse(self.classify(fixture(ExecStart=cmd))["effective_execstart_expected"])

    def test_extra_hook_refused(self):
        self.assertFalse(self.classify(fixture(ExecStartPre="{ path=/bin/true ; argv[]=/bin/true }"))["no_extra_exec_hooks"])

    def test_environment_file_refused(self):
        self.assertFalse(self.classify(fixture(EnvironmentFiles="/tmp/secrets"))["no_environment_file"])

    def test_dynamic_user_refused(self):
        self.assertFalse(self.classify(fixture(DynamicUser="yes"))["no_dynamic_or_root_redirect"])

    def test_not_running_refused(self):
        self.assertFalse(self.classify(fixture(ActiveState="inactive"))["loaded_running"])

    def test_missing_property_refused(self):
        with self.assertRaises(ValueError):
            self.classify(fixture().replace("DynamicUser=no\n", ""))

    def test_optional_unset_properties_may_be_omitted(self):
        raw = fixture()
        for key in mod.OPTIONAL_EMPTY:
            raw = raw.replace(key + "=\\n", "")
        self.assertTrue(all(self.classify(raw).values()))

    def test_omitted_optional_does_not_hide_configured_hook(self):
        raw = fixture(ExecStartPre="{ path=/bin/true ; argv[]=/bin/true }")
        for key in mod.OPTIONAL_EMPTY - {"ExecStartPre"}:
            raw = raw.replace(key + "=\\n", "")
        self.assertFalse(self.classify(raw)["no_extra_exec_hooks"])

    def test_duplicate_property_refused(self):
        with self.assertRaises(ValueError):
            self.classify(fixture() + "LoadState=loaded\n")

    def test_credentials_not_in_results(self):
        self.assertNotIn("SENSITIVE", repr(self.classify(fixture())))

if __name__ == "__main__":
    unittest.main()
