"""Offline synthetic tests for sanitized systemd topology inventory."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inventory_service_topology as topology


class ServiceTopologyTests(unittest.TestCase):
    def test_no_command_arguments_passwords_or_environment_values(self):
        secret = "SECRET-PRIVATE-TEST-DO-NOT-LEAK-ABC123"
        body = f"""[Unit]
Description=Test instance {secret}
After=network-online.target openclaw-gateway.service
Wants=openclaw-gateway.service
[Service]
Type=oneshot
WorkingDirectory=/home/example/{secret}
Environment=PASSWORD={secret} TOKEN={secret}
EnvironmentFile=/home/example/{secret}.env
ExecStart=/usr/bin/python3 /home/example/bin/bob-moltbook-scout --token {secret}
ExecStartPre=/bin/sh -c 'echo {secret}'
NoNewPrivileges=true
ProtectSystem=strict
Restart=no
[Install]
WantedBy=default.target
"""
        review = topology.safe_directives(body)
        encoded = json.dumps(review)
        self.assertNotIn(secret, encoded)
        self.assertNotIn("PASSWORD=", encoded)
        self.assertNotIn("/home/example", encoded)
        self.assertIn("openclaw-gateway.service", review["related_units"])
        self.assertIn("network-online.target", review["related_units"])
        self.assertEqual(review["exec_directives"]["ExecStart"], 1)
        self.assertEqual(review["environment_directives"]["Environment"], 1)
        self.assertEqual(review["environment_directives"]["EnvironmentFile"], 1)
        self.assertEqual(review["service_type"], "oneshot")
        self.assertEqual(review["restart_policy"], "no")
        self.assertIn("NoNewPrivileges", review["security_directives_present"])

    def test_detects_duplicate_scout_in_different_scopes(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            u = p / "user"
            s = p / "system"
            for scope in (u, s):
                scope.mkdir()
                f = scope / "bob-moltbook-scout.service"
                f.write_text("[Service]\nExecStart=/usr/bin/python3 bob-moltbook-scout\n")
            (u / "bob-moltbook-scout.timer").write_text(
                "[Timer]\nOnCalendar=*:0/10\nPersistent=true\n")
            d = u / "bob-moltbook-scout.service.d"
            d.mkdir()
            (d / "v05.conf").write_text("[Service]\nEnvironment=TOKEN=PRIVATE\n")
            result = topology.collect([("user", u), ("system", s)], states=False)
            self.assertEqual(result["counts"]["files"], 4)
            self.assertEqual(result["counts"]["units"], 3)
            self.assertIn("bob-moltbook-scout.service",
                          result["unit_names_in_both_scopes"])
            self.assertIn("bob-activity-manager.service",
                          result["expected_units_not_found"])
            self.assertNotIn("PRIVATE", json.dumps(result))
            self.assertEqual(len(result["states"]), 0)

    def test_symlink_units_are_not_followed(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            src = p / "actual"
            src.write_text("[Service]\nEnvironment=PASSWORD=NEVER-DISCLOSE\n")
            folder = p / "systemd"
            folder.mkdir()
            (folder / "bob-activity-manager.service").symlink_to(src)
            result = topology.collect([("user", folder)], states=False)
            self.assertEqual(result["unit_files"][0]["type"],
                             "unreadable_or_symlink")
            self.assertNotIn("NEVER-DISCLOSE", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
