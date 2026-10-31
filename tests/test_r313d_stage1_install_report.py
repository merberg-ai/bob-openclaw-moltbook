"""R3.13d post-migration installed attestation is read-only and phase-aware.

All HTTP, installed paths, credentials, units and SQLite are mocked.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch,MagicMock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_r313d_stage1_installed as report


def evidence(*, migrated=False):
    return {
        "reviewed_off_gates":{"production_off_source":True},
        "publisher":{
            "effective_unit_shape":"reviewed_shape",
            "installed_file":"owner_controlled_regular",
            "updater_registry":"verified_registry_hash",
            "review_blockers":[],
        },
        "host":{
            "legacy_schema":"match",
            "private_copy_eligible":not migrated,
            "additive_schema":"existing_needs_review" if migrated else "absent",
            "r3_settings":"explicit_off" if migrated else "absent_off",
            "review_blockers":["additive_schema_not_empty"] if migrated else [],
        },
    }


class R313DInstalledReportTests(unittest.TestCase):
    @staticmethod
    def registry(release=None):
        return {
            "format":"bob-updater-v1",
            "release":release or report.RELEASE,
            "files":{name:"a"*64 for name in report.REQUIRED},
        }

    def test_refuses_uninstalled_release_without_loopback_credential_read(self):
        with patch.object(report.updater,"registry",return_value=self.registry(
                "v0.8.0-shadow4")),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.prior,"collect",return_value=evidence()),\
             patch.object(report.migration,"_db_review",
                          return_value={"state":"eligible"}),\
             patch.object(report.migration,"_journal_state",return_value="absent"),\
             patch.object(report,"_dashboard") as browser:
            result=report.inspect()
            self.assertFalse(result["installed_acceptance"])
            self.assertEqual(result["owner_controls_ui"],"not_checked")
            self.assertFalse(result["new_r3_publication_rights"])
            browser.assert_not_called()

    def test_stage1_verified_pre_migration_without_granting_rights(self):
        with patch.object(report.updater,"registry",return_value=self.registry()),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.prior,"collect",return_value=evidence()),\
             patch.object(report.migration,"_db_review",
                          return_value={"state":"eligible"}),\
             patch.object(report.migration,"_journal_state",return_value="absent"),\
             patch.object(report,"_dashboard",
                          return_value="authenticated_read_only_page"):
            result=report.inspect()
            self.assertTrue(result["installed_acceptance"])
            self.assertEqual(result["r3_schema"],"eligible")
            self.assertEqual(result["migration_journal"],"absent")
            self.assertEqual(result["r3_send_guards"],"verified_off")
            self.assertEqual(result["moltbook_api_calls"],0)
            self.assertFalse(result["manual_canary_authorized"])

    def test_post_migration_schema_ready_journal_complete_is_valid_install(self):
        with patch.object(report.updater,"registry",return_value=self.registry()),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.prior,"collect",
                          return_value=evidence(migrated=True)),\
             patch.object(report.migration,"_db_review",
                          return_value={"state":"ready","attempts":23,"uncertain":0}),\
             patch.object(report.migration,"_journal_state",return_value="complete"),\
             patch.object(report,"_dashboard",
                          return_value="authenticated_read_only_page"):
            result=report.inspect()
            self.assertTrue(result["installed_acceptance"])
            self.assertEqual(result["off_first_release"],"verified")
            self.assertEqual(result["r3_schema"],"ready")
            self.assertEqual(result["migration_journal"],"complete")
            self.assertFalse(result["new_r3_publication_rights"])
            self.assertFalse(result["manual_canary_authorized"])

    def test_refuse_wrong_phase_or_source_gate_without_reading_credentials(self):
        bad=evidence(migrated=True)
        bad["reviewed_off_gates"]["production_off_source"]=False
        with patch.object(report.updater,"registry",return_value=self.registry()),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.prior,"collect",return_value=bad),\
             patch.object(report.migration,"_db_review",return_value={"state":"ready"}),\
             patch.object(report.migration,"_journal_state",return_value="complete"),\
             patch.object(report,"_dashboard") as browser:
            result=report.inspect()
            self.assertFalse(result["installed_acceptance"])
            self.assertEqual(result["owner_controls_ui"],"not_checked")
            browser.assert_not_called()
        good=evidence(migrated=True)
        with patch.object(report.updater,"registry",return_value=self.registry()),\
             patch.object(report.updater,"live_ok",return_value=True),\
             patch.object(report.prior,"collect",return_value=good),\
             patch.object(report.migration,"_db_review",return_value={"state":"ready"}),\
             patch.object(report.migration,"_journal_state",return_value="prepared"),\
             patch.object(report,"_dashboard") as browser:
            self.assertFalse(report.inspect()["installed_acceptance"])
            browser.assert_not_called()

    def test_http_retries_but_requires_correct_authenticated_r3_off_labels(self):
        bad=MagicMock()
        bad.status=200
        bad.read.return_value=b"<html>some other dashboard</html>"
        good=MagicMock()
        good.status=200
        good.read.return_value=(
            b"Bob R3 Controls / R3 automatic publishing OFF (compiled locked)")
        client=MagicMock()
        client.getresponse.side_effect=[bad,bad,bad,good]
        with patch.object(report.updater,"authorization",return_value="Basic fake"),\
             patch.object(report,"HTTPConnection",return_value=client),\
             patch.object(report.time,"sleep"):
            self.assertEqual(report._dashboard(),"unverified")
            self.assertEqual(report._dashboard(),"authenticated_read_only_page")
        self.assertEqual(client.request.call_count,4)

    def test_unverified_refusal_page_is_not_accepted(self):
        bad=MagicMock()
        bad.status=200
        bad.read.return_value=(
            b"Bob R3 Controls R3 automatic publishing compiled locked "
            b"Owner controls remain unavailable")
        client=MagicMock()
        client.getresponse.return_value=bad
        with patch.object(report.updater,"authorization",return_value="Basic fake"),\
             patch.object(report,"HTTPConnection",return_value=client),\
             patch.object(report.time,"sleep"):
            self.assertEqual(report._dashboard(),"unverified")

    def test_invalid_cli_arguments_never_call_host(self):
        with patch.object(report,"inspect") as inspect:
            self.assertEqual(report.main(["--install"]),2)
            self.assertEqual(report.main(["--apply-off"]),2)
            inspect.assert_not_called()


if __name__=="__main__":
    unittest.main()
