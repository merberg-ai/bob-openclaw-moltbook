"""R3 one-command host acceptance report tests, entirely synthetic."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]
import report_r3_cutover_installed as report
import r3_service_handoff as handoff


def states():
    return {
        handoff.PUBLISHER_TIMER:handoff.Snapshot("loaded","active","enabled"),
        handoff.PUBLISHER_SERVICE:handoff.Snapshot("loaded","inactive","static"),
        handoff.SCOUT_TIMER:handoff.Snapshot("loaded","active","enabled"),
        handoff.SHADOW_TIMER:handoff.Snapshot("loaded","active","enabled"),
        handoff.SHADOW_SERVICE:handoff.Snapshot("loaded","inactive","static"),
        handoff.SERVICE:handoff.Snapshot("not-found","inactive","not-found"),
        handoff.TIMER:handoff.Snapshot("not-found","inactive","not-found"),
        handoff.COMPETITOR_TIMER:handoff.Snapshot("not-found","inactive","not-found"),
        handoff.COMPETITOR_SERVICE:handoff.Snapshot("not-found","inactive","not-found"),
    }


def expected(**changes):
    data={"schema":"ready","new_r3_owner_controls":"default_off",
          "attempted_jobs":23,"uncertain_jobs":0}
    data.update(changes)
    return data


class IntegratedInstalledReportTests(unittest.TestCase):
    def good(self,**opts):
        state=states()
        state.update(opts.pop("states",{}))
        kwargs={
            "operator": lambda:True, "installed":lambda:True,
            "health":lambda:True,"route":lambda:True,
            "units":lambda:report._unit_gate(probe=state.__getitem__),
            "dbreview":lambda:expected(),
            "publisher_report":lambda:{
                "effective_service":"reviewed_shape",
                "effective_timer":"reviewed_shape","review_blockers":[]}
        }
        kwargs.update(opts)
        return report.inspect(**kwargs)

    def test_complete_accepted_off_first_result_without_host_change(self):
        r=self.good()
        self.assertEqual(r["acceptance"],"PASS")
        self.assertEqual(r["historical_attempts"],23)
        self.assertEqual(r["uncertain_delivery_rows"],0)
        self.assertEqual(r["authenticated_https_health"],"PASS")
        self.assertEqual(r["r3_proposal_timer"],"OFF")
        self.assertFalse(r["wrote_files_or_database"])
        self.assertFalse(r["changed_systemd_or_publisher"])
        self.assertFalse(r["r3_real_publishing_authorized"])
        self.assertEqual(r["public_moltbook_requests"],0)
        self.assertFalse(r["external_duplicate_posting_excluded"])

    def test_untrusted_release_or_account_never_opens_host_data(self):
        calls=[]
        def prohibited():
            calls.append("host")
            raise AssertionError("early refusal must not call later checks")
        for kwargs in (
            {"operator":lambda:False,"installed":prohibited},
            {"operator":lambda:True,"installed":lambda:False,"health":prohibited},
        ):
            with self.subTest(kwargs=tuple(kwargs)):
                self.assertEqual(self.good(**kwargs)["acceptance"],"NOT_VERIFIED")
        self.assertEqual(calls,[])

    def test_https_or_r3_route_failure_not_accepted(self):
        for flag in ("health","route"):
            with self.subTest(flag=flag):
                self.assertEqual(self.good(**{flag:lambda:False})["acceptance"],
                                 "NOT_VERIFIED")

    def test_owner_consent_not_off_or_schema_invalid_refuses(self):
        for modifications in (
            {"new_r3_owner_controls":"requires_owner_review"},
            {"schema":"unverified"},
            {"attempted_jobs":None},
        ):
            with self.subTest(modifications=modifications):
                r=self.good(dbreview=lambda:expected(**modifications))
                self.assertEqual(r["acceptance"],"NOT_VERIFIED")

    def test_new_proposal_or_competing_publisher_timer_blocks_initial_acceptance(self):
        variations=(
            {handoff.TIMER:handoff.Snapshot("loaded","active","enabled")},
            {handoff.COMPETITOR_TIMER:handoff.Snapshot("loaded","active","enabled")},
            {handoff.SHADOW_TIMER:handoff.Snapshot("loaded","inactive","disabled")},
            {handoff.PUBLISHER_TIMER:handoff.Snapshot("loaded","inactive","disabled")},
        )
        for change in variations:
            with self.subTest(change=change):
                self.assertEqual(self.good(states=change)["acceptance"],
                                 "NOT_VERIFIED")

    def test_untrusted_publisher_effective_shape_fails_closed(self):
        r=self.good(publisher_report=lambda:{
            "effective_service":"unverified","effective_timer":"reviewed_shape",
            "review_blockers":["publisher_exec_not_verified"]})
        self.assertEqual(r["acceptance"],"NOT_VERIFIED")

    def test_command_has_no_install_or_publish_flags(self):
        with patch.object(report,"inspect",return_value={
                "account":"verified","installed_signed_release":"ok",
                "authenticated_https_health":"PASS",
                "authenticated_r3_controls":"PASS",
                "r3_owner_settings":"default_off",
                "single_existing_publisher":"PASS",
                "r3_proposal_timer":"OFF","historical_attempts":23,
                "uncertain_delivery_rows":0,"acceptance":"PASS"}):
            self.assertEqual(report.main(["--postcheck"]),0)
            self.assertEqual(report.main(["--apply"]),2)
            self.assertEqual(report.main(["--send"]),2)
            self.assertEqual(report.main(["--restart"]),2)

if __name__=="__main__":
    unittest.main()
