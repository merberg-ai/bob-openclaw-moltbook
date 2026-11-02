"""R4 real OpenClaw transport compatibility, without starting OpenClaw or HTTP.

The source-level proposal worker must use a distinct *accepted* OpenClaw
main-agent session rather than a synthetic callback that ignores validation.
"""
from __future__ import annotations

from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src/lib/bob")]
import bob_r4_agent as agent
from bob_v08 import shadow


class Observed:
    run_id="20261101T151033Z"
    post_id="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
    author="AnotherAgent"
    title="Synthetic source"
    excerpt="Model input remains untrusted DATA"


NOW=datetime(2026,11,1,16,0,tzinfo=timezone.utc)
OFF=dict.fromkeys(("comment","reply","post","upvote","follow","unfollow"),"off")


class LiveTransportCompatibilityTests(unittest.TestCase):
    def test_real_validated_openclaw_transport_accepts_r4_proposal_session(self):
        seen=[]
        reply=json.dumps({
            "type":"skip","source_run":Observed.run_id,
            "target_id":Observed.post_id,"reason":"",
            "text":"","title":"","submolt":"","parent_id":""})
        def fake_cli(args,**kwargs):
            seen.append((args,kwargs))
            return SimpleNamespace(returncode=0,stdout=json.dumps({
                "status":"ok","result":{"payloads":[{"text":reply}]}}))
        with patch.object(shadow.subprocess,"run",side_effect=fake_cli):
            decision=agent.decide(Observed,modes={**OFF,"upvote":"propose"},
                                  model=shadow.openclaw_decide,now=NOW)
        self.assertEqual(decision.kind,"skip")
        self.assertEqual(len(seen),1)
        command=seen[0][0]
        self.assertEqual(command[0:4],["openclaw","agent","--agent","main"])
        session=command[command.index("--session-key")+1]
        self.assertEqual(session,"moltbook-v08-shadow-r4-proposal-"+Observed.run_id)
        self.assertTrue(session.startswith("moltbook-v08-shadow-"))
        self.assertIn("--message-file",command)
        self.assertNotIn("--tools",command)

    def test_original_invalid_r4_prefix_rejected_before_cli(self):
        with patch.object(shadow.subprocess,"run",
                          side_effect=AssertionError("unverified session reached CLI")):
            with self.assertRaisesRegex(ValueError,"unexpected_shadow_session"):
                shadow.openclaw_decide("private proposal","moltbook-v08-r4-proposal-"+Observed.run_id)


if __name__=="__main__":
    unittest.main()
