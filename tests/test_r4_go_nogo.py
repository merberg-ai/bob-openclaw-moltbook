"""Read-only consolidated R4 source + real-host gate and output boundary.

No live host, network, credentials, services, SQLite, release or Moltbook calls.
The actual candidate builder/source audit is separately tested in CI.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import report_r4_go_nogo as gate
import report_r4_preinstall


def source_ok():
    return {
        "candidate": gate.EXPECTED_SOURCE,
        "current_unchanged": gate.EXPECTED_INSTALLED,
        "files": 23,
        "candidate_source_build": "PASS",
        "exact_https_generated_manager": True,
        "all_new_auto_modes_compiled_off": True,
        "legacy_r3_publisher_not_replaced": True,
        "install_authorized": False,
        "real_social_action_authorized": False,
    }


def host_ok():
    return {
        "currently_installed_expected": gate.EXPECTED_INSTALLED,
        "target_candidate": gate.EXPECTED_SOURCE,
        "ready_for_separate_owner_install_prompt": True,
        "installation_authorized": False,
        "real_r4_send_authorized": False,
        "checks": {name: True for name in report_r4_preinstall.REQUIRED},
    }


class R4GoNogoTests(unittest.TestCase):
    def test_success_means_only_future_separate_review_not_install(self):
        report = gate.inspect(source_probe=source_ok, host_probe=host_ok)
        self.assertTrue(report["candidate_source_verified"])
        self.assertEqual(report["candidate_files_checked"], 23)
        self.assertTrue(report["live_host_readiness_verified"])
        self.assertTrue(report["ready_for_separate_release_review"])
        self.assertEqual(report["blockers"], [])
        for key in ("r4_installed_by_report", "install_authorized_by_report",
                    "real_r4_social_sends_authorized",
                    "host_files_changed_by_report", "systemd_changed_by_report",
                    "database_changed_by_report"):
            self.assertFalse(report[key], key)
        self.assertEqual(report["moltbook_api_requests_by_report"], 0)

    def test_each_host_requirement_refuses_without_source_failure(self):
        for name in report_r4_preinstall.REQUIRED:
            with self.subTest(name=name):
                def missing_one():
                    result = host_ok()
                    result["checks"][name] = False
                    result["ready_for_separate_owner_install_prompt"] = False
                    return result
                report = gate.inspect(source_probe=source_ok, host_probe=missing_one)
                self.assertTrue(report["candidate_source_verified"])
                self.assertFalse(report["live_host_readiness_verified"])
                self.assertEqual(report["blockers"], ["host_" + name])
                self.assertFalse(report["ready_for_separate_release_review"])

    def test_wrong_manifest_or_real_send_arming_never_passes(self):
        for key, value in (
            ("files", 22),
            ("current_unchanged", "v0.8.0-r3skip1"),
            ("real_social_action_authorized", True),
            ("install_authorized", True),
            ("all_new_auto_modes_compiled_off", False),
        ):
            with self.subTest(key=key):
                def source_drift():
                    return {**source_ok(), key: value}
                report = gate.inspect(source_probe=source_drift, host_probe=host_ok)
                self.assertFalse(report["candidate_source_verified"])
                self.assertEqual(report["blockers"], ["candidate_source_review"])
                self.assertFalse(report["ready_for_separate_release_review"])

    def test_bad_host_attestation_and_exceptions_fail_without_secret_output(self):
        def broken_source():
            raise RuntimeError("private source token DO_NOT_ECHO")
        def broken_host():
            raise OSError("private path DO_NOT_ECHO")
        report = gate.inspect(source_probe=broken_source, host_probe=broken_host)
        self.assertFalse(report["candidate_source_verified"])
        self.assertFalse(report["live_host_readiness_verified"])
        self.assertNotIn("DO_NOT_ECHO", json.dumps(report))
        bad = host_ok()
        bad["ready_for_separate_owner_install_prompt"] = False
        report = gate.inspect(source_probe=source_ok, host_probe=lambda: bad)
        self.assertEqual(report["blockers"], ["host_attestation_incomplete"])
        self.assertFalse(report["ready_for_separate_release_review"])

    def test_cli_never_changes_state_and_requires_nonroot_check_flag(self):
        safe = gate.inspect(source_probe=source_ok, host_probe=host_ok)
        with patch.object(gate.os, "geteuid", return_value=1000), \
             patch.object(gate, "inspect", return_value=safe):
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(gate.main(["--check"]), 0)
            parsed = json.loads(output.getvalue())
            self.assertTrue(parsed["ready_for_separate_release_review"])
            self.assertFalse(parsed["install_authorized_by_report"])
            self.assertEqual(gate.main(["--install"]), 2)
        with patch.object(gate.os, "geteuid", return_value=0), \
             patch.object(gate, "inspect",
                          side_effect=AssertionError("root should not inspect")):
            self.assertEqual(gate.main(["--check"]), 1)

    def test_report_does_not_invoke_mutating_actions(self):
        code = (ROOT / "scripts/report_r4_go_nogo.py").read_text("utf-8")
        for forbidden in (
            "systemctl restart", "systemctl stop", "systemctl enable",
            "UPDATE to", "requests.post", "urllib.request", "api_key(",
            "updater.update(", "migrate_candidate(", "create_verified_backup(",
            "releases/current.json",
        ):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
