"""Offline unit-state report tests: no services, network or credentials touched."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_service_readiness as r


class ReadinessTests(unittest.TestCase):
    def report(self):
        return {
            "report_version": 1,
            "purpose": "private read-only Bob service topology; not a deployable unit template",
            "unit_files": [
                {"scope": "user", "unit": "bob-moltbook-scout.service", "kind": "unit"},
                {"scope": "system", "unit": "bob-moltbook-scout.service", "kind": "unit"},
                {"scope": "user", "unit": "bob-moltbook-scout.timer", "kind": "unit"},
                {"scope": "system", "unit": "bob-moltbook-scout.timer", "kind": "unit"},
                {"scope": "user", "unit": "bob-activity-manager.service", "kind": "unit"},
                {"scope": "user", "unit": "bob-activity-manager.service", "kind": "dropin"},
                {"scope": "system", "unit": "unexpected-PRIVATE-password.service"},
            ],
        }

    def test_strips_untrusted_unit_names_and_checks_whitelist(self):
        pairs = r.unit_pairs(self.report())
        self.assertEqual(len(pairs), 5)
        self.assertNotIn("unexpected-PRIVATE-password.service", str(pairs))
        with self.assertRaises(ValueError):
            r.systemd_status("system", "unexpected-PRIVATE-password.service")

    def test_sanitizes_subprocess_values_and_never_shells_out(self):
        class Result:
            returncode = 0
            stdout = ("ActiveState=active\nSubState=running\nLoadState=loaded\n"
                      "UnitFileState=enabled\nEnvironment=PASSWORD=never-print-this\n")
        with patch.object(r.subprocess, "run", return_value=Result()) as cmd:
            got = r.systemd_status("user", "bob-moltbook-scout.service")
        self.assertEqual(got, {
            "load": "loaded", "active": "active",
            "sub": "running", "enabled": "enabled",
        })
        self.assertNotIn("never-print-this", str(got))
        self.assertEqual(cmd.call_args.args[0][0], "systemctl")
        self.assertNotIn("shell", cmd.call_args.kwargs)

    def test_unknown_status_is_not_echoed(self):
        class Result:
            returncode = 0
            stdout = "ActiveState=secret=private\nUnitFileState=possibly-malicious\n"
        with patch.object(r.subprocess, "run", return_value=Result()):
            got = r.systemd_status("system", "bob-moltbook-scout.timer")
        self.assertEqual(got["active"], "unknown")
        self.assertEqual(got["enabled"], "unknown")

    def test_private_report_permissions_and_no_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "inventory-20261028.json"
            path.write_text(json.dumps(self.report()))
            path.chmod(0o600)
            self.assertEqual(len(r.read_private_report(path)["unit_files"]), 7)
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "permissions"):
                r.read_private_report(path)
            path.chmod(0o600)
            link = Path(temp) / "inventory-link.json"
            link.symlink_to(path)
            with self.assertRaisesRegex(ValueError, "symlink"):
                r.read_private_report(link)

    def test_readiness_summary_uses_safe_mock_only(self):
        states = r.summarize(self.report(), get_status=lambda scope, name: {
            "load": "loaded", "active": "inactive" if scope == "system" else "active",
            "sub": "dead" if scope == "system" else "running",
            "enabled": "disabled" if scope == "system" else "enabled",
        })
        self.assertEqual(len(states), 5)
        self.assertEqual([s for s in states
                          if s["unit"] == "bob-moltbook-scout.service" and
                          s["scope"] == "system"][0]["enabled"], "disabled")


if __name__ == "__main__":
    unittest.main()
