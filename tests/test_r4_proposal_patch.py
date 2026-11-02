"""R4 proposal-only signed patch: source, host and social-send boundaries.

Source audit is real and read-only. Host and OpenClaw effects are mocked.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater
import report_r4_proposal_candidate as audit


def host_ready():
    return {
        "release":"v0.8.0-autonomy1",
        "signed_installed_source":True,
        "legacy_and_r3_registry":True,
        "authenticated_https":True,
        "new_r4_routes":True,
        "versioned_additive_schema":True,
        "publisher_inactive_at_check":True,
        "new_r4_actions_attempted":0,
    }


class ProposalPatchTests(unittest.TestCase):
    def test_exact_source_and_transport_are_reviewed_but_not_promoted(self):
        report=audit.inspect()
        self.assertEqual(report["current_release_unchanged"],"v0.8.0-autonomy1")
        self.assertEqual(report["candidate_release"],"v0.8.0-r4propose1")
        self.assertEqual(report["candidate_files"],4)
        self.assertTrue(report["main_agent_transport_compatible"])
        self.assertTrue(report["all_r4_public_sends_hard_off"])
        for key in ("proposal_schedule_enabled","owner_modes_edited",
                    "database_migrated","installed_on_omen"):
            self.assertFalse(report[key])
        self.assertEqual(set(report["verified_source_hashes"]),set(audit.ALLOWED))

    def test_patch_preflight_requires_previous_signed_live_R4_acceptance(self):
        with patch("report_r4_installed.inspect",return_value=host_ready()), \
             patch.object(updater,"r4_publisher_inactive",return_value=True):
            self.assertTrue(updater.preflight_r4_proposal_patch())
        for key,new_value in (
            ("release","v0.8.0-r3canary1"),
            ("signed_installed_source",False),
            ("legacy_and_r3_registry",False),
            ("authenticated_https",False),
            ("new_r4_routes",False),
            ("versioned_additive_schema",False),
            ("publisher_inactive_at_check",False),
            ("new_r4_actions_attempted",1),
        ):
            with self.subTest(key=key), \
                 patch("report_r4_installed.inspect",
                       return_value={**host_ready(),key:new_value}), \
                 patch.object(updater,"r4_publisher_inactive",return_value=True):
                self.assertFalse(updater.preflight_r4_proposal_patch())
        with patch("report_r4_installed.inspect",return_value=host_ready()), \
             patch.object(updater,"r4_publisher_inactive",return_value=False):
            self.assertFalse(updater.preflight_r4_proposal_patch())

    def test_patch_preflight_exceptions_never_approve(self):
        with patch("report_r4_installed.inspect",
                   side_effect=ValueError("private credential, must not log")):
            self.assertFalse(updater.preflight_r4_proposal_patch())

    def test_candidate_manifest_is_exact_and_unpromoted(self):
        c=json.loads((ROOT/"releases/candidates/r4-propose1-one-shot.json").read_text())
        live=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(live["release"],"v0.8.0-autonomy1")
        self.assertEqual(c["release"],"v0.8.0-r4propose1")
        self.assertEqual(c["from"],live["release"])
        self.assertTrue(c["restart_manager"])
        self.assertEqual({f["name"] for f in c["files"]},set(audit.ALLOWED))
        self.assertNotIn("bob-moltbook-publisher",{f["name"] for f in c["files"]})
        self.assertNotIn("bob-r4-propose",{f["name"] for f in c["files"]})
        self.assertNotIn("bob-r4-publisher",{f["name"] for f in c["files"]})

    def test_source_report_has_no_install_or_network_cli(self):
        self.assertEqual(audit.main(["--install"]),2)
        self.assertEqual(audit.main(["--check"]),0)
        source=(ROOT/"scripts/report_r4_proposal_candidate.py").read_text()
        for banned in ("systemctl restart","requests.post","migrate_candidate(",
                       "updater.update(", "subprocess.run(", "api_key(",
                       "set_pause(", "set_mode("):
            self.assertNotIn(banned,source)


if __name__=="__main__":
    unittest.main()
