"""R4 preinstall gate must accept the SIGNED R3 CANARY, not obsolete R3.

Fixed allowlisted host probes only. No production home, systemd modifications,
dashboard POST, DB migrations, Moltbook calls or secrets in test output.
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
import bob_release_updater as updater
import report_r4_preinstall as gate


class R4PreinstallTests(unittest.TestCase):
    def passed(self):
        return {name: (lambda: True) for name in gate.REQUIRED}

    def test_exact_signed_canary_is_ready_even_if_old_r3_gate_is_incompatible(self):
        report = gate.inspect(checks=self.passed())
        self.assertEqual(report["currently_installed_expected"], "v0.8.0-r3canary1")
        self.assertEqual(report["target_candidate"], "v0.8.0-autonomy1")
        self.assertEqual(report["blockers"], [])
        self.assertTrue(report["ready_for_separate_owner_install_prompt"])
        self.assertFalse(report["installation_authorized"])
        self.assertFalse(report["real_r4_send_authorized"])
        with patch.object(updater, "preflight_r3_diagnostics_only",
                          side_effect=AssertionError("obsolete R3 gate invoked")), \
             patch.object(gate, "inspect", return_value=report):
            self.assertTrue(updater.preflight_r4_installation())

    def test_each_missing_host_requirement_fails_closed(self):
        for broken in gate.REQUIRED:
            with self.subTest(broken=broken):
                checks = self.passed()
                checks[broken] = lambda: False
                result = gate.inspect(checks=checks)
                self.assertEqual(result["blockers"], [broken])
                self.assertFalse(result["ready_for_separate_owner_install_prompt"])
                self.assertFalse(result["systemd_changed"])
                self.assertFalse(result["database_changed"])
                self.assertEqual(result["moltbook_requests"], 0)

    def test_exceptions_and_non_boolean_probe_outputs_refuse(self):
        checks = self.passed()
        checks["signed_r3_canary"] = lambda: "yes"
        checks["publisher_inactive"] = lambda: (_ for _ in ()).throw(
            RuntimeError("synthetic secret must not escape"))
        result = gate.inspect(checks=checks)
        self.assertEqual(result["blockers"],
                         ["publisher_inactive", "signed_r3_canary"])
        self.assertNotIn("secret", json.dumps(result))
        with patch.object(gate, "inspect", side_effect=RuntimeError("no host")):
            self.assertFalse(updater.preflight_r4_installation())
        with self.assertRaisesRegex(ValueError, "r4_unreviewed_preinstall_probes"):
            gate.inspect(checks={"unexpected": lambda: True})

    def test_probe_uses_signed_canary_old_units_and_hardened_tls_only(self):
        from unittest.mock import patch
        import report_r3_canary_installed as canary
        import report_r3_diagnostic_installed as diagnostics
        import report_r38_effective_units as effective
        with patch.object(canary, "_signed_scope", return_value=True), \
             patch.object(diagnostics, "_units_ok", return_value=True), \
             patch.object(effective, "report", return_value={
                 "effective_service": "reviewed_shape",
                 "effective_timer": "reviewed_shape",
                 "review_blockers": [],
                 "cutover_authorized": False,
             }), \
             patch.object(updater, "authorization", return_value="Basic fake"), \
             patch.object(updater, "healthy", return_value=True) as healthy:
            self.assertTrue(gate.signed_r3_canary())
            self.assertTrue(gate.existing_worker_topology())
            self.assertTrue(gate.effective_original_publisher_units())
            self.assertTrue(gate.authenticated_https())
            healthy.assert_called_once_with("Basic fake", release=gate.RELEASE)
        with patch.object(effective, "report", return_value={
            "effective_service": "reviewed_shape",
            "effective_timer": "reviewed_shape",
            "review_blockers": ["unexpected drop-in"],
            "cutover_authorized": False,
        }):
            self.assertFalse(gate.effective_original_publisher_units())

    def test_no_incomplete_update_journal_and_cli_safe(self):
        with patch.object(updater, "read_journal", return_value={
            "phase": "migrated"}):
            self.assertFalse(gate.no_incomplete_update())
        with patch.object(updater, "read_journal", return_value={
            "phase": "complete"}):
            self.assertTrue(gate.no_incomplete_update())
        with patch.object(gate.os, "geteuid", return_value=1000), \
             patch.object(gate, "inspect", return_value=gate.inspect(
                 checks=self.passed())):
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(gate.main(["--check"]), 0)
            text = output.getvalue()
            self.assertIn('"installation_authorized":false', text)
            self.assertNotIn("synthetic secret", text)
        self.assertEqual(gate.main(["--apply"]), 2)

    def test_candidate_is_still_unpromoted_and_updater_invokes_new_gate(self):
        import inspect
        from pathlib import Path
        candidate=json.loads((ROOT/
            "releases/candidates/r4-autonomy1-consolidated.json").read_text())
        live=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(live["release"], "v0.8.0-r3canary1")
        self.assertEqual(candidate["from"], live["release"])
        source=inspect.getsource(updater.main)
        self.assertIn('not preflight_r4_installation()', source)
        self.assertNotIn(
            'plan["release"]=="v0.8.0-autonomy1" and not preflight_r3_diagnostics_only()',
            source)


if __name__ == "__main__":
    unittest.main()
