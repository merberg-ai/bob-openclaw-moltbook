"""R3 code upgrade host preflight gate, purely mocked production readers."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import report_g2_recovery as g2
import report_r3_cutover_inventory as inventory


class R3OffFirstPreinstallTests(unittest.TestCase):
    def test_accepted_g2_and_idle_legacy_publisher_allow_review(self):
        with patch.object(g2,"inspect",return_value={
                "host_gate":"PASS","historical_uncertain":0}) as g,\
             patch.object(inventory,"unit_facts",return_value={
                 "load":"loaded","active":"inactive"}) as u:
            self.assertTrue(updater.preflight_r3_consolidated_offfirst())
            g.assert_called_once_with("baseline")
            u.assert_called_once_with(
                "user","bob-moltbook-publisher.service")

    def test_any_host_drift_or_running_publisher_blocks_before_code_changes(self):
        for status in ("active","activating","failed","unknown"):
            with self.subTest(status=status),\
                 patch.object(g2,"inspect",return_value={
                     "host_gate":"PASS","historical_uncertain":0}),\
                 patch.object(inventory,"unit_facts",return_value={
                     "load":"loaded","active":status}):
                self.assertFalse(updater.preflight_r3_consolidated_offfirst())
        for check in ("NOT_VERIFIED",None):
            with patch.object(g2,"inspect",return_value={
                    "host_gate":check,"historical_uncertain":0}),\
                 patch.object(inventory,"unit_facts",
                              side_effect=AssertionError("must not inspect")):
                self.assertFalse(updater.preflight_r3_consolidated_offfirst())
        with patch.object(g2,"inspect",return_value={
                "host_gate":"PASS","historical_uncertain":None}),\
             patch.object(inventory,"unit_facts",
                          side_effect=AssertionError("must not inspect")):
            self.assertFalse(updater.preflight_r3_consolidated_offfirst())

    def test_probe_failure_is_a_refusal_not_permission(self):
        with patch.object(g2,"inspect",side_effect=ValueError("unknown")):
            self.assertFalse(updater.preflight_r3_consolidated_offfirst())
        with patch.object(g2,"inspect",return_value={
                "host_gate":"PASS","historical_uncertain":0}),\
             patch.object(inventory,"unit_facts",side_effect=OSError("offline")):
            self.assertFalse(updater.preflight_r3_consolidated_offfirst())

    def test_typed_update_stays_separate_from_preinstall_gate(self):
        source=(ROOT/"scripts/bob_release_updater.py").read_text()
        self.assertIn(
            'if plan["release"]=="v0.8.0-cutover1" and not preflight_r3_consolidated_offfirst():',
            source)
        self.assertLess(source.index('if plan["release"]=="v0.8.0-cutover1" and not'),
                        source.index('input("Type UPDATE to back up and install'))
        self.assertIn("r3_offfirst_preinstall_host_or_publisher_unverified",source)
        self.assertNotIn('subprocess.run(["systemctl","--user","stop"',source)
        self.assertNotIn("restore_database",source)


if __name__=="__main__":
    unittest.main()
