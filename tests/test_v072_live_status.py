"""v0.7.2 bounded read-only status contract tests."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/lib/bob"))
sys.path.insert(0, str(ROOT / "scripts"))
import bob_live_status as status
import build_v072_settings_candidate as builder

class StatusContracts(unittest.TestCase):
    def test_fixed_allowlist(self):
        with self.assertRaises(ValueError):
            status.unit_state("arbitrary.service")
    def test_no_systemd_mutations(self):
        with patch.object(status.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "active\n"
            self.assertEqual(status.unit_state("openclaw-gateway.service"), "running")
            self.assertEqual(run.call_args.args[0][:3], ["systemctl", "--user", "is-active"])
    def test_stalled_systemd_is_unknown(self):
        with patch.object(status.subprocess, "run", side_effect=status.subprocess.TimeoutExpired("systemctl", 1)):
            self.assertEqual(status.unit_state("bob-moltbook-scout.service"), "unknown")
    def test_page_and_api_routes(self):
        manager, navigation = builder.build()
        self.assertIn(b'elif self.path == "/system/status"', manager)
        self.assertIn(b'elif self.path == "/api/system/status"', manager)
        self.assertIn(b'("/system/status", "System status", "System status")', navigation)
    def test_labels_are_not_fake_job_progress(self):
        self.assertEqual(len(status.UNITS), 4)
        self.assertNotIn("generating", status.snapshot.__code__.co_consts)
if __name__ == "__main__":
    unittest.main()
