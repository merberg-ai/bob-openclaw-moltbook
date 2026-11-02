"""Synthetic tests for redacted systemd unit directive inventory."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts/inspect_v071_unit_directives.py"
spec = importlib.util.spec_from_file_location("v071_unit_directives", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SAMPLE = """# /home/demo/.config/systemd/user/bob-activity-manager.service
[Unit]
Description=Demo
[Service]
ExecStart=/home/demo/.local/bin/bob-activity-manager
WorkingDirectory=/home/demo
Environment=SECRET=never-print-me
# /home/demo/.config/systemd/user/bob-activity-manager.service.d/override.conf
[Service]
EnvironmentFile=/home/demo/private/keys
ExecStartPre=/home/demo/private/hook
"""


class UnitDirectiveTests(unittest.TestCase):
    def test_flags_without_private_values(self):
        results = mod.classify(SAMPLE)
        self.assertEqual(results["EnvironmentFile"], "YES")
        self.assertEqual(results["ExecStartPre"], "YES")
        self.assertEqual(results["ExecStartPost"], "NO")
        self.assertEqual(results["ExecCondition"], "NO")
        self.assertNotIn("never-print-me", repr(results))
        self.assertNotIn("/home/demo", repr(results))

    def test_blank_override_reset_is_unknown(self):
        results = mod.classify(SAMPLE + "EnvironmentFile=\n")
        self.assertEqual(results["EnvironmentFile"], "UNKNOWN")

    def test_nonservice_does_not_count(self):
        raw = "# /home/demo/unit\n[Unit]\nEnvironmentFile=secret\n[Service]\nExecStart=/bin/true\n"
        self.assertEqual(mod.classify(raw)["EnvironmentFile"], "NO")

    def test_missing_source_marker_refused(self):
        with self.assertRaises(ValueError):
            mod.classify("[Service]\nExecStart=/bin/true\n")

    def test_malformed_service_line_refused(self):
        with self.assertRaises(ValueError):
            mod.classify(SAMPLE + "unexpected bytes\n")


if __name__ == "__main__":
    unittest.main()
