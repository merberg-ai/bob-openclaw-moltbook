"""Offline checks of R3 diagnostics release and private read-only host gate.

These run without a real user systemd, network, credentials or Moltbook API.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as upd
import r3_service_handoff as h
import report_r3_diagnostic_installed as report


def states():
    return {
        h.PUBLISHER_TIMER:h.Snapshot("loaded","active","enabled"),
        h.PUBLISHER_SERVICE:h.Snapshot("loaded","inactive","static"),
        h.SCOUT_TIMER:h.Snapshot("loaded","active","enabled"),
        h.SHADOW_TIMER:h.Snapshot("loaded","inactive","disabled"),
        h.SHADOW_SERVICE:h.Snapshot("loaded","inactive","static"),
        h.SERVICE:h.Snapshot("loaded","failed","static"),
        h.TIMER:h.Snapshot("loaded","active","enabled"),
        h.COMPETITOR_TIMER:h.Snapshot("not-found","inactive","not-found"),
        h.COMPETITOR_SERVICE:h.Snapshot("not-found","inactive","not-found"),
    }


class DiagnosticsReleaseTests(unittest.TestCase):
    def test_promoted_3_file_package_is_only_off_first_diagnostics(self):
        historical=json.loads((ROOT/"releases/candidates/r3-format1-offfirst.json").read_text())
        candidate=json.loads(
            (ROOT/"releases/candidates/r3-diag1-offfirst.json").read_text())
        self.assertEqual(historical["from"],candidate["release"])
        self.assertEqual(historical["release"],"v0.8.0-r3format1")
        self.assertEqual(candidate["from"],"v0.8.0-cutover1")
        self.assertFalse(historical["restart_manager"])
        names={item["name"] for item in historical["files"]}
        self.assertEqual(names,
                         {"bob-release-updater","bobctl","bob_r3_package.pyz"})
        self.assertEqual(upd.manager_transport(historical["release"]),"https")
        self.assertEqual(upd.manager_transport(historical["from"]),"https")
        for forbidden in ("bob-moltbook-publisher","bob-activity-manager",
                          "bob-r3-propose","bob-r3-publisher"):
            self.assertNotIn(forbidden,names)
        import build_r313d_off_package as builder
        blob,_=builder.build()
        self.assertTrue(blob)
        self.assertTrue(upd.release_bytes(ROOT,historical["files"][2]))

    def test_signature_gate_does_not_change_original_unit_journal_template(self):
        self.assertEqual(h.UNIT_TEXT[h.TIMER].count("OnUnitInactiveSec=35min"),1)
        self.assertIn('("v0.8.0-cutover1","v0.8.0-r3diag1","v0.8.0-r3format1","v0.8.0-r3skip1")',
                      (ROOT/"scripts/r3_service_handoff.py").read_text())
        self.assertFalse(h._installed_cutover_off.__doc__ and
                         "Moltbook POST" in h._installed_cutover_off.__doc__)

    def test_signed_r3diag1_source_preflight_allows_failed_oneshot(self):
        st=states()
        with patch.object(h,"_installed_cutover_off",return_value=True), \
             patch.object(h,"_status_all",return_value=st):
            self.assertTrue(upd.preflight_r3_diagnostics_only())
            st[h.SERVICE]=h.Snapshot("loaded","active","static")
            self.assertFalse(upd.preflight_r3_diagnostics_only())
            st[h.SERVICE]=h.Snapshot("loaded","inactive","static")
            self.assertTrue(upd.preflight_r3_diagnostics_only())
            st[h.PUBLISHER_SERVICE]=h.Snapshot("loaded","active","static")
            self.assertFalse(upd.preflight_r3_diagnostics_only())
        with patch.object(h,"_installed_cutover_off",return_value=False):
            self.assertFalse(upd.preflight_r3_diagnostics_only())

    def test_competing_publisher_or_shadow_timer_blocks_diagnostic_update(self):
        st=states()
        with patch.object(h,"_installed_cutover_off",return_value=True), \
             patch.object(h,"_status_all",return_value=st):
            st[h.COMPETITOR_TIMER]=h.Snapshot("loaded","active","enabled")
            self.assertFalse(upd.preflight_r3_diagnostics_only())
            st[h.COMPETITOR_TIMER]=h.Snapshot("not-found","inactive","not-found")
            st[h.SHADOW_TIMER]=h.Snapshot("loaded","active","enabled")
            self.assertFalse(upd.preflight_r3_diagnostics_only())
            st[h.SHADOW_TIMER]=h.Snapshot("loaded","inactive","disabled")
            st[h.SCOUT_TIMER]=h.Snapshot("loaded","inactive","disabled")
            self.assertFalse(upd.preflight_r3_diagnostics_only())

    def test_installed_readonly_report_is_fail_closed(self):
        opts={"owner":lambda:True,"installed":lambda:True,
              "package":lambda:True,"health":lambda:True,
              "controls":lambda:True,"units":lambda:True}
        good=report.inspect(**opts)
        self.assertEqual(good["acceptance"],"PASS")
        self.assertEqual(good["r3_proposal_only_timer"],"ACTIVE")
        self.assertFalse(good["host_or_database_changed"])
        self.assertEqual(good["moltbook_requests"],0)
        self.assertFalse(good["r3_real_publication_authorized"])
        for name in opts:
            modified=dict(opts)
            modified[name]=lambda:False
            with self.subTest(name=name):
                self.assertEqual(report.inspect(**modified)["acceptance"],
                                 "NOT_VERIFIED")

    def test_installed_archive_marker_proves_distinct_safe_categories(self):
        import build_r313d_off_package as builder
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            (base/"bob_r3_package.pyz").write_bytes(builder.build()[0])
            with patch.object(report.upd,"BIN",base), \
                 patch.object(report,"_verified_release",return_value=True):
                self.assertTrue(report._diagnostic_package_present())
            (base/"bob_r3_package.pyz").write_bytes(b"corrupt")
            with patch.object(report.upd,"BIN",base), \
                 patch.object(report,"_verified_release",return_value=True):
                self.assertFalse(report._diagnostic_package_present())


if __name__=="__main__":
    unittest.main()
