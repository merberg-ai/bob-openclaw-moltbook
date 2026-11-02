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
    def test_historical_four_file_proposal_patch_is_archived_not_offered(self):
        from pathlib import Path
        old=json.loads((ROOT/"releases/candidates/r4-propose1-one-shot.json")
                       .read_text())
        self.assertEqual(old["release"],"v0.8.0-r4propose1")
        self.assertEqual(old["from"],"v0.8.0-autonomy1")
        self.assertEqual(len(old["files"]),4)
        self.assertEqual(
            {item["name"] for item in old["files"]},set(audit.ALLOWED))
        # The signed old release is already installed on OMEN; re-offering
        # or auditing it as the CURRENT offer is not permitted.
        current=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(current["release"],"v0.8.0-r4schedule1")
        with self.assertRaisesRegex(ValueError,"r4_proposal_patch_chain_unverified"):
            audit.inspect()

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

    def test_historical_manifest_not_current_offer(self):
        old=json.loads((ROOT/"releases/candidates/r4-propose1-one-shot.json")
                       .read_text())
        current=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(old["release"],"v0.8.0-r4propose1")
        intermediate=json.loads((ROOT/
            "releases/candidates/r4-format1-json-reliability.json").read_text())
        self.assertEqual(intermediate["from"],old["release"])
        self.assertEqual(current["from"],intermediate["release"])
        self.assertEqual(current["release"],"v0.8.0-r4schedule1")
        self.assertNotIn("bob-moltbook-publisher",
                         {f["name"] for f in current["files"]})
        self.assertNotIn("bob-r4-publisher",
                         {f["name"] for f in current["files"]})

    def test_source_report_has_no_install_or_network_cli(self):
        self.assertEqual(audit.main(["--install"]),2)
        self.assertEqual(audit.main(["--check"]),1)
        source=(ROOT/"scripts/report_r4_proposal_candidate.py").read_text()
        for banned in ("systemctl restart","requests.post","migrate_candidate(",
                       "updater.update(", "subprocess.run(", "api_key(",
                       "set_pause(", "set_mode("):
            self.assertNotIn(banned,source)


if __name__=="__main__":
    unittest.main()
