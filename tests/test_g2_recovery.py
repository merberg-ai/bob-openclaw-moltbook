"""G2 host-readiness synthetic checks. No live systemd/SQLite/network."""
from __future__ import annotations
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_g2_recovery as g2


class G2ReadOnlyTests(unittest.TestCase):
    def facts(self):
        result=[]
        for scope, name in g2.REQUIRED_ACTIVE:
            result.append({"scope":scope,"unit":name,"load":"loaded",
                           "active":"active","enabled":"enabled"})
        for scope, name in g2.REQUIRED_INERT:
            result.append({"scope":scope,"unit":name,"load":"loaded",
                           "active":"inactive","enabled":"disabled"})
        return result

    def check(self, rows=None, *, source=True, history=None, publisher=True,
              linger="yes"):
        if rows is None:
            rows=self.facts()
        state={(row["scope"],row["unit"]):row for row in rows}
        if history is None:
            history={"state":"ready","attempts":23,"uncertain":0}
        with patch.object(g2,"_operator",return_value=True), \
             patch.object(g2.https,"inspect",return_value={
                 "acceptance":"PASS" if source else "NOT_VERIFIED"}), \
             patch.object(g2,"_facts",side_effect=lambda s,n:state[(s,n)]), \
             patch.object(g2.publisher,"report",return_value={
                 "effective_service":"reviewed_shape" if publisher else "unverified",
                 "effective_timer":"reviewed_shape",
                 "review_blockers":[]}), \
             patch.object(g2.migration,"_db_review",return_value=history), \
             patch.object(g2.migration,"_journal_state",return_value="complete"), \
             patch.object(g2.startup,"linger_status",return_value=linger):
            return g2.inspect("baseline")

    def test_healthy_state_passes_without_claiming_reboot_or_no_duplicates(self):
        result=self.check()
        self.assertEqual(result["host_gate"],"PASS")
        self.assertEqual(result["historical_attempts"],23)
        self.assertEqual(result["historical_uncertain"],0)
        self.assertFalse(result["windows_startup_or_reboot_observed"])
        self.assertFalse(result["actual_duplicate_posting_excluded"])
        self.assertFalse(result["r3_public_send_authorized"])
        self.assertEqual(result["moltbook_requests"],0)
        self.assertFalse(result["database_or_credentials_changed"])

    def test_owner_reported_static_scout_and_absent_candidates_pass(self):
        """Reproduce actual G2 JSON: inactive/static system Scout service."""
        rows=self.facts()
        for row in rows:
            if (row["scope"],row["unit"]) == (
                    "system","bob-moltbook-scout.service"):
                row["enabled"]="static"
            if row["unit"].startswith("bob-r3-candidate-publisher."):
                row.update(load="not-found",active="inactive",enabled="unknown")
        result=self.check(rows)
        self.assertEqual(result["host_gate"],"PASS")
        self.assertEqual(result["historical_attempts"],23)
        self.assertFalse(result["actual_duplicate_posting_excluded"])

    def test_static_system_scout_requires_inert_installed_timer(self):
        for timer_load,timer_active,timer_enabled,expected in (
                ("loaded","inactive","disabled","PASS"),
                ("loaded","inactive","masked","PASS"),
                ("loaded","inactive","masked-runtime","PASS"),
                ("loaded","inactive","enabled","NOT_VERIFIED"),
                ("loaded","active","disabled","NOT_VERIFIED"),
                ("loaded","inactive","unknown","NOT_VERIFIED"),
                ("not-found","inactive","unknown","NOT_VERIFIED"),
                ("loaded","inactive","static","NOT_VERIFIED")):
            rows=self.facts()
            for row in rows:
                if (row["scope"],row["unit"]) == (
                        "system","bob-moltbook-scout.service"):
                    row["enabled"]="static"
                if (row["scope"],row["unit"]) == (
                        "system","bob-moltbook-scout.timer"):
                    row.update(load=timer_load,active=timer_active,
                               enabled=timer_enabled)
            with self.subTest(timer=(timer_load,timer_active,timer_enabled)):
                self.assertEqual(self.check(rows)["host_gate"],expected)

    def test_static_exception_never_applies_to_other_competitors(self):
        for scope,name in (
                ("system","bob-moltbook-scout.timer"),
                ("user","bob-r3-candidate-publisher.service"),
                ("user","bob-r3-candidate-publisher.timer")):
            rows=self.facts()
            for row in rows:
                if (row["scope"],row["unit"]) == (scope,name):
                    row["enabled"]="static"
            with self.subTest(unit=(scope,name)):
                self.assertEqual(self.check(rows)["host_gate"],"NOT_VERIFIED")

    def test_active_static_scout_service_still_blocks(self):
        rows=self.facts()
        for row in rows:
            if (row["scope"],row["unit"]) == (
                    "system","bob-moltbook-scout.service"):
                row.update(enabled="static",active="active")
        self.assertEqual(self.check(rows)["host_gate"],"NOT_VERIFIED")

    def test_https_r3_source_drift_blocks(self):
        self.assertEqual(self.check(source=False)["host_gate"],"NOT_VERIFIED")

    def test_live_legacy_duplicate_system_scout_blocks(self):
        rows=self.facts()
        for row in rows:
            if row["scope"]=="system" and row["unit"]=="bob-moltbook-scout.timer":
                row["active"]="active"
        self.assertEqual(self.check(rows)["host_gate"],"NOT_VERIFIED")

    def test_enabled_dormant_system_scout_blocks_reboot(self):
        rows=self.facts()
        for row in rows:
            if row["scope"]=="system" and row["unit"]=="bob-moltbook-scout.timer":
                row["enabled"]="enabled"
        self.assertEqual(self.check(rows)["host_gate"],"NOT_VERIFIED")

    def test_candidate_publisher_enabled_or_active_blocks(self):
        for state_key in ("enabled","active"):
            rows=self.facts()
            for row in rows:
                if row["unit"]=="bob-r3-candidate-publisher.timer":
                    row[state_key]="enabled" if state_key=="enabled" else "active"
            with self.subTest(key=state_key):
                self.assertEqual(self.check(rows)["host_gate"],"NOT_VERIFIED")

    def test_missing_required_manager_or_timer_enabled_blocks(self):
        for problem in ("manager_inactive","timer_disabled"):
            rows=self.facts()
            if problem=="manager_inactive":
                rows[0]["active"]="inactive"
            else:
                rows[1]["enabled"]="disabled"
            self.assertEqual(self.check(rows)["host_gate"],"NOT_VERIFIED")

    def test_unreviewed_effective_publisher_blocks(self):
        self.assertEqual(self.check(publisher=False)["host_gate"],"NOT_VERIFIED")

    def test_absent_or_bad_history_blocks(self):
        for result in (
            {"state":"eligible","attempts":23,"uncertain":0},
            {"state":"ready","attempts":None,"uncertain":0},
            {"state":"ready","attempts":23,"uncertain":-1},
        ):
            with self.subTest(result=result):
                x=self.check(history=result)
                self.assertEqual(x["host_gate"],"NOT_VERIFIED")
                self.assertIsNone(x["historical_attempts"])

    def test_absent_owner_blocks_checks(self):
        with patch.object(g2,"_operator",return_value=False), \
             patch.object(g2.https,"inspect") as network, \
             patch.object(g2,"_facts") as units:
            result=g2.inspect("baseline")
            self.assertEqual(result["host_gate"],"NOT_VERIFIED")
            network.assert_not_called()
            units.assert_not_called()

    def test_missing_unit_probe_fails_closed(self):
        with patch.object(g2,"_operator",return_value=True), \
             patch.object(g2.https,"inspect",return_value={"acceptance":"PASS"}), \
             patch.object(g2,"_facts",side_effect=OSError("offline")), \
             patch.object(g2.publisher,"report",return_value={
                 "effective_service":"reviewed_shape",
                 "effective_timer":"reviewed_shape","review_blockers":[]}), \
             patch.object(g2.migration,"_db_review",return_value={
                 "state":"ready","attempts":23,"uncertain":0}), \
             patch.object(g2.migration,"_journal_state",return_value="complete"), \
             patch.object(g2.startup,"linger_status",return_value="unavailable"):
            x=g2.inspect("postcheck")
            self.assertEqual(x["host_gate"],"NOT_VERIFIED")
            self.assertEqual(x["unit_states"],[])

    def test_two_phases_and_no_mutation_cli(self):
        with patch.object(g2,"_operator",return_value=True), \
             patch.object(g2,"inspect",return_value={
                 "host_gate":"PASS",
                 "format":"bob-g2-host-observation-v1"
             }) as inspect, redirect_stdout(StringIO()):
            self.assertEqual(g2.main(["--baseline"]),0)
            inspect.assert_called_with("baseline")
            self.assertEqual(g2.main(["--postcheck"]),0)
            inspect.assert_called_with("postcheck")
            self.assertEqual(g2.main(["--install"]),2)
            self.assertEqual(g2.main(["--restart"]),2)
            self.assertEqual(g2.main(["--publish"]),2)

    def test_inert_helper_rejects_unknown_and_live(self):
        row={"load":"not-found","active":"inactive","enabled":"unknown"}
        self.assertTrue(g2._inert(row))
        row["load"]="loaded"
        self.assertFalse(g2._inert(row))
        row["enabled"]="disabled"
        self.assertTrue(g2._inert(row))
        row["active"]="active"
        self.assertFalse(g2._inert(row))


if __name__=="__main__":
    unittest.main()
