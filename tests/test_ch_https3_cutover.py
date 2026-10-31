"""CH-HTTPS3 live cutover report negative/positive tests. All probes mocked."""
from __future__ import annotations
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_ch_https3_cutover as report

class CutoverReportTests(unittest.TestCase):
    def test_preflight_needs_accepted_ch1_and_cert_and_off_and_timers(self):
        with patch.object(report,"_manager_active",return_value=True),\
             patch.object(report,"_timers_active",return_value=True),\
             patch.object(report,"_host_source_off",return_value=True),\
             patch.object(report,"_ca_verified",return_value=True),\
             patch.object(report,"_release_verified",return_value=True) as registry,\
             patch.object(report.previous,"inspect",return_value={
                 "installation_acceptance":"PASS",
                 "current_manager_transport":"http_pre_cutover"
             }),patch.object(report,"_https_route") as future:
            row=report.inspect("preflight")
            self.assertEqual(row["acceptance"],"PASS")
            self.assertEqual(row["authenticated_https_health"],"not_checked")
            self.assertEqual(row["plain_http_on_old_port"],"not_checked")
            registry.assert_called_once_with(report.BEFORE)
            future.assert_not_called()

    def test_postflight_requires_https_and_explicit_http_refusal(self):
        with patch.object(report,"_manager_active",return_value=True),\
             patch.object(report,"_timers_active",return_value=True),\
             patch.object(report,"_host_source_off",return_value=True),\
             patch.object(report,"_ca_verified",return_value=True),\
             patch.object(report,"_release_verified",return_value=True),\
             patch.object(report.updater,"manager_transport",return_value="https"),\
             patch.object(report.updater,"healthy",return_value=True),\
             patch.object(report.updater,"authorization",return_value="Basic fake"),\
             patch.object(report,"_authenticated_r3_https",return_value=True),\
             patch.object(report,"_plaintext_refused",return_value=True):
            row=report.inspect("installed")
            self.assertEqual(row["acceptance"],"PASS")
            self.assertFalse(row["r3_public_send_authorized"])
        with patch.object(report,"_manager_active",return_value=True),\
             patch.object(report,"_timers_active",return_value=True),\
             patch.object(report,"_host_source_off",return_value=True),\
             patch.object(report,"_ca_verified",return_value=True),\
             patch.object(report,"_release_verified",return_value=True),\
             patch.object(report.updater,"manager_transport",return_value="https"),\
             patch.object(report.updater,"healthy",return_value=True),\
             patch.object(report.updater,"authorization",return_value="Basic fake"),\
             patch.object(report,"_authenticated_r3_https",return_value=True),\
             patch.object(report,"_plaintext_refused",return_value=False):
            row=report.inspect("installed")
            self.assertEqual(row["acceptance"],"NOT_VERIFIED")
            self.assertEqual(row["plain_http_on_old_port"],"accepted_or_unverified")

    def test_wrong_ca_registry_service_or_source_gate_fail_closed(self):
        cases=[
            ("_manager_active",False),
            ("_timers_active",False),
            ("_host_source_off",False),
            ("_ca_verified",False),
            ("_release_verified",False),
        ]
        for key,value in cases:
            with self.subTest(key=key),\
                 patch.object(report,"_manager_active",return_value=True),\
                 patch.object(report,"_timers_active",return_value=True),\
                 patch.object(report,"_host_source_off",return_value=True),\
                 patch.object(report,"_ca_verified",return_value=True),\
                 patch.object(report,"_release_verified",return_value=True),\
                 patch.object(report,key,return_value=value),\
                 patch.object(report,"_authenticated_r3_https") as browser:
                result=report.inspect("installed")
                self.assertEqual(result["acceptance"],"NOT_VERIFIED")
                browser.assert_not_called()

    def test_verified_auth_and_anonymous_get(self):
        good=(200,b"Bob R3 Controls R3 automatic publishing compiled locked")
        with patch.object(report,"_https_route",
             side_effect=[good,(401,b"")]) as client:
            self.assertTrue(report._authenticated_r3_https())
            client.assert_any_call("/r3",authenticated=True)
            client.assert_any_call("/r3",authenticated=False)
        with patch.object(report,"_https_route",
             side_effect=[good,(200,b"")]):
            self.assertFalse(report._authenticated_r3_https())
        with patch.object(report,"_https_route",
             side_effect=[(200,good[1]+b"Owner controls remain unavailable"),
                          (401,b"")]):
            self.assertFalse(report._authenticated_r3_https())

    def test_plain_http_that_responds_even_401_is_not_accepted(self):
        conn=MagicMock()
        conn.getresponse.return_value=MagicMock(status=401)
        with patch.object(report,"HTTPConnection",return_value=conn):
            self.assertFalse(report._plaintext_refused())
        conn.request.side_effect=ConnectionResetError("synthetic TLS port")
        with patch.object(report,"HTTPConnection",return_value=conn):
            self.assertTrue(report._plaintext_refused())

    def test_fixed_public_sha_pinned_to_owner_report(self):
        self.assertEqual(report.CA_FINGERPRINT,
            "af47c380af49eaf5b51683eb2cb1b6455eba019e754e09e295a0a3eeedc1f196")
        self.assertEqual(report.ADDRESS,"127.0.0.1")
        self.assertEqual(report.PORT,18790)

    def test_no_mutating_cli_mode(self):
        with patch.object(report,"inspect") as inspect:
            self.assertEqual(report.main(["--apply"]),2)
            self.assertEqual(report.main(["--switch"]),2)
            inspect.assert_not_called()


if __name__=="__main__":
    unittest.main()
