"""Offline R4 advisory policy invariants; never calls a live service."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bob_v08.r4_policy import Controls, Evidence, Intent, review


class R4PolicyTests(unittest.TestCase):
    def setUp(self):
        self.intent = Intent("follow", "20261101T040000Z", "public_agent_1",
                             "Relevant verified discussion")
        self.evidence = Evidence(source_verified=True, target_verified=True,
                                 endpoint_verified=True, source_fresh=True,
                                 cooldown_clear=True)
        self.controls = Controls(
            modes={"follow": "propose"}, total_daily_cap=2,
            action_daily_caps={"follow": 1})

    def test_all_action_categories_are_default_off(self):
        for kind in ("comment","reply","post","upvote","follow","unfollow"):
            item = Intent(kind, "validsource", "" if kind == "post" else "target",
                          "A reason", "A draft" if kind in
                          ("post","comment","reply") else "")
            result = review(item, self.evidence, Controls())
            self.assertEqual(result.status, "denied")
            self.assertFalse(result.dispatch_authorized)

    def test_propose_only_never_grants_dispatch(self):
        result = review(self.intent, self.evidence, self.controls)
        self.assertEqual(result.status, "candidate_propose")
        self.assertFalse(result.dispatch_authorized)

    def test_unverified_endpoint_stays_off_even_in_auto(self):
        controls = Controls(modes={"follow": "auto"},
                            owner_auto_opt_ins=frozenset({"follow"}),
                            total_daily_cap=2,
                            action_daily_caps={"follow": 1})
        evidence = Evidence(source_verified=True, target_verified=True,
                            source_fresh=True, cooldown_clear=True)
        result = review(self.intent, evidence, controls)
        self.assertEqual(result.reason, "unverified_api_endpoint")

    def test_auto_requires_independent_action_opt_in(self):
        controls = Controls(modes={"follow": "auto"}, total_daily_cap=2,
                            action_daily_caps={"follow": 1})
        self.assertEqual(review(self.intent, self.evidence, controls).reason,
                         "explicit_auto_opt_in_absent")
        controls = Controls(modes={"follow": "auto"},
                            owner_auto_opt_ins=frozenset({"follow"}),
                            total_daily_cap=2,
                            action_daily_caps={"follow": 1})
        result = review(self.intent, self.evidence, controls)
        self.assertEqual(result.status, "candidate_auto")
        self.assertFalse(result.dispatch_authorized)

    def test_pause_duplicate_cooldown_and_budget_fail_closed(self):
        cases = (
            (self.evidence, Controls(modes={"follow":"propose"}, paused=True,
             total_daily_cap=2, action_daily_caps={"follow":1}),
             "global_pause"),
            (Evidence(source_verified=True, target_verified=True,
             endpoint_verified=True, source_fresh=True, cooldown_clear=True,
             already_attempted=True), self.controls,
             "duplicate_or_uncertain_attempt"),
            (Evidence(source_verified=True, target_verified=True,
             endpoint_verified=True, source_fresh=True), self.controls,
             "cooldown_not_clear"),
            (self.evidence, Controls(modes={"follow":"propose"},
             total_daily_cap=1, total_attempted_today=1,
             action_daily_caps={"follow":1}), "global_daily_budget"),
        )
        for evidence, controls, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(review(self.intent,evidence,controls).reason,
                                 reason)

    def test_unfollow_needs_remote_following_not_local_friend(self):
        unfollow = Intent("unfollow",self.intent.source_id,
                          self.intent.target_id,self.intent.reason)
        controls = Controls(modes={"unfollow":"propose"}, total_daily_cap=2,
                            action_daily_caps={"unfollow":1})
        self.assertEqual(review(unfollow,self.evidence,controls).reason,
                         "remote_following_not_verified")
        e = Evidence(source_verified=True,target_verified=True,
                     endpoint_verified=True,source_fresh=True,
                     cooldown_clear=True,remote_following_verified=True)
        self.assertEqual(review(unfollow,e,controls).status,
                         "candidate_propose")

    def test_untrusted_identifiers_body_and_self_interaction_denied(self):
        self.assertEqual(review(Intent("follow","s","https://bad","r"),
                                self.evidence,self.controls).status,"denied")
        self.assertEqual(review(Intent("follow","s","target","r","body"),
                                self.evidence,self.controls).status,"denied")
        e = Evidence(source_verified=True,target_verified=True,
                     endpoint_verified=True,source_fresh=True,
                     cooldown_clear=True,target_is_self=True)
        self.assertEqual(review(self.intent,e,self.controls).reason,
                         "self_interaction")


if __name__ == "__main__":
    unittest.main()
