"""R3.13d staged-release read-only installed acceptance, mocked and offline.

No real manager, database, credentials, HTTP or systemd interaction.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_r313d_stage1_installed as report


class R313DInstalledReportTests(unittest.TestCase):
    def test_refuses_uninstalled_release_without_loopback_credential_read(self):
        with patch.object(report.updater,"registry",return_value={
                "format":"bob-updater-v1",
                "release":"v0.8.0-shadow4",
                "files":{name:"a"*64 for name in report.REQUIRED}}),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.prior,"collect") as host,\
             patch.object(report,"_dashboard") as browser:
            host.return_value={
                "reviewed_off_gates":{"production_off_source":True},
                "publisher":{"effective_unit_shape":"reviewed_shape",
                             "updater_registry":"verified_registry_hash"},
                "host":{"r3_settings":"absent_off"}}
            result=report.inspect()
            self.assertFalse(result["installed_acceptance"])
            self.assertEqual(result["owner_controls_ui"],"not_checked")
            self.assertFalse(result["new_r3_publication_rights"])
            browser.assert_not_called()

    def test_stage1_verified_only_when_installed_hashes_source_gates_and_auth_get_pass(self):
        valid={
            "format":"bob-updater-v1",
            "release":report.RELEASE,
            "files":{name:"a"*64 for name in report.REQUIRED}}
        checked={
            "reviewed_off_gates":{"production_off_source":True},
            "publisher":{"effective_unit_shape":"reviewed_shape",
                         "updater_registry":"verified_registry_hash"},
            "host":{"r3_settings":"absent_off"}}
        with patch.object(report.updater,"registry",return_value=valid),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.prior,"collect",return_value=checked),\
             patch.object(report,"_dashboard",
                          return_value="authenticated_read_only_page"):
            result=report.inspect()
            self.assertTrue(result["installed_acceptance"])
            self.assertEqual(result["off_first_release"],"verified")
            self.assertEqual(result["r3_send_guards"],"verified_off")
            self.assertEqual(result["moltbook_api_calls"],0)
            self.assertFalse(result["manual_canary_authorized"])
        checked["reviewed_off_gates"]["production_off_source"]=False
        with patch.object(report.updater,"registry",return_value=valid),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.prior,"collect",return_value=checked),\
             patch.object(report,"_dashboard") as browser:
            self.assertFalse(report.inspect()["installed_acceptance"])
            browser.assert_not_called()

    def test_http_response_requires_actual_r3_controls_not_just_any_200(self):
        from unittest.mock import MagicMock
        bad=MagicMock()
        bad.status=200
        bad.read.return_value=b"<html>some other dashboard</html>"
        client=MagicMock()
        client.getresponse.return_value=bad
        with patch.object(report.updater,"authorization",return_value="Basic fake"),\
             patch.object(report,"HTTPConnection",return_value=client):
            self.assertEqual(report._dashboard(),"unverified")
        good=MagicMock()
        good.status=200
        good.read.return_value=(b"Bob R3 Controls / "
            b"R3 automatic publishing OFF (compiled locked)")
        client.getresponse.return_value=good
        with patch.object(report.updater,"authorization",return_value="Basic fake"),\
             patch.object(report,"HTTPConnection",return_value=client):
            self.assertEqual(report._dashboard(),
                             "authenticated_read_only_page")
        self.assertEqual(client.request.call_count,2)

    def test_invalid_cli_arguments_never_call_host(self):
        with patch.object(report,"inspect") as inspect:
            self.assertEqual(report.main(["--install"]),2)
            self.assertEqual(report.main(["--apply-off"]),2)
            inspect.assert_not_called()


if __name__=="__main__":
    unittest.main()
