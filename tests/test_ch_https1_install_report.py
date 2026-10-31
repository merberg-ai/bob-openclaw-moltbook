"""CH-HTTPS1 post-install attestation: mocked, no live host actions."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_ch_https1_installed as report

class CHHTTPS1ReportTests(unittest.TestCase):
    @staticmethod
    def record(release=None):
        return {
            "format":"bob-updater-v1",
            "release":release or report.RELEASE,
            "files":{f:"a"*64 for f in report.REQUIRED},
        }

    @staticmethod
    def host():
        return {"no_real_changes":True}

    def test_new_two_file_release_and_read_only_http_manager_pass(self):
        with patch.object(report.updater,"registry",return_value=self.record()),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.migration,"_db_review",
                          return_value={"state":"ready","attempts":23,"uncertain":0}),\
             patch.object(report.migration,"_journal_state",return_value="complete"),\
             patch.object(report.host,"collect",return_value=self.host()),\
             patch.object(report.migration,"_host_phase_accepted",return_value=True),\
             patch.object(report.updater,"healthy",return_value=True) as healthy,\
             patch.object(report.updater,"authorization",
                          return_value="Basic synthetic"),\
             patch.object(report.stage,"_dashboard",
                          return_value="authenticated_read_only_page"):
            result=report.inspect()
            self.assertEqual(result["installation_acceptance"],"PASS")
            self.assertEqual(result["r3_schema"],"ready")
            self.assertEqual(result["migration_journal"],"complete")
            self.assertEqual(result["current_manager_transport"],"http_pre_cutover")
            self.assertEqual(result["future_tls_transport"],"verified_strict_https")
            self.assertFalse(result["tls_activated"])
            self.assertFalse(result["new_r3_send_rights"])
            healthy.assert_called_once_with("Basic synthetic",release=report.RELEASE)

    def test_wrong_release_or_off_gate_refuses_without_health_probe(self):
        for release,off in (("v0.8.0-r3stage1",True),
                            (report.RELEASE,False)):
            with self.subTest(release=release,off=off):
                with patch.object(report.updater,"registry",
                                  return_value=self.record(release)),\
                     patch.object(report.updater,"live_ok",return_value=True),\
                     patch.object(report.migration,"_db_review",
                                  return_value={"state":"ready"}),\
                     patch.object(report.migration,"_journal_state",
                                  return_value="complete"),\
                     patch.object(report.host,"collect",return_value=self.host()),\
                     patch.object(report.migration,"_host_phase_accepted",
                                  return_value=off),\
                     patch.object(report.updater,"healthy") as healthy,\
                     patch.object(report.stage,"_dashboard") as browser:
                    self.assertEqual(report.inspect()["installation_acceptance"],
                                     "NOT_VERIFIED")
                    healthy.assert_not_called()
                    browser.assert_not_called()

    def test_failed_authenticated_page_does_not_count_as_ready(self):
        with patch.object(report.updater,"registry",return_value=self.record()),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.migration,"_db_review",
                          return_value={"state":"ready"}),\
             patch.object(report.migration,"_journal_state",return_value="complete"),\
             patch.object(report.host,"collect",return_value=self.host()),\
             patch.object(report.migration,"_host_phase_accepted",return_value=True),\
             patch.object(report.updater,"healthy",return_value=True),\
             patch.object(report.updater,"authorization",
                          return_value="Basic synthetic"),\
             patch.object(report.stage,"_dashboard",return_value="unverified"):
            self.assertEqual(report.inspect()["installation_acceptance"],
                             "NOT_VERIFIED")

    def test_no_install_or_tls_mutating_arguments(self):
        with patch.object(report,"inspect") as inspected:
            self.assertEqual(report.main(["--apply"]),2)
            self.assertEqual(report.main(["--install"]),2)
            inspected.assert_not_called()

if __name__=="__main__":
    unittest.main()
