"""R4 source-verified agent decision schema, no actual model/network calls."""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_decision as decision


@dataclass(frozen=True)
class Source:
    run_id:str="20261101T151033Z"
    post_id:str="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
    author:str="Interesting_Agent"


NOW=datetime(2026,11,1,20,0,tzinfo=timezone.utc)
SOURCE=Source()


def raw(kind="skip", **values):
    obj=dict(type=kind,source_run=SOURCE.run_id,target_id=SOURCE.post_id,
             reason="",text="",title="",submolt="",parent_id="")
    obj.update(values)
    return json.dumps(obj,sort_keys=True,separators=(",",":"))


class R4DecisionTests(unittest.TestCase):
    def test_one_exact_source_skip_not_an_action(self):
        d=decision.parse(raw(),SOURCE,now=NOW)
        self.assertEqual(d.kind,"skip")
        self.assertEqual(d.source_run,SOURCE.run_id)
        self.assertEqual(json.loads(decision.exact_example(SOURCE))["type"],"skip")

    def test_valid_single_post_upvote_and_repeat_observed_author_follow(self):
        upvote=decision.parse(
            raw("upvote",reason="Relevant carefully checked discussion"),
            SOURCE,now=NOW)
        self.assertEqual(upvote.target_id,SOURCE.post_id)
        follow=decision.parse(
            raw("follow",target_id=SOURCE.author,
                reason="Several useful previous discussions"),
            SOURCE,now=NOW,author_observations=2)
        self.assertEqual(follow.target_id,SOURCE.author)
        original=decision.parse(
            raw("post",target_id="",title="Lessons in human review latency",
                submolt="general",text="Bob's original specific perspective",
                reason="Worth exploring in public once owner reviews"),
            SOURCE,now=NOW)
        self.assertEqual(original.submolt,"general")

    def test_model_cannot_pick_unobserved_agent_or_post(self):
        for malformed in (
            raw("follow",target_id="Another_Agent",reason="Interesting"),
            raw("follow",target_id="http://wrong",reason="Interesting"),
            raw("upvote",target_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                reason="Interesting"),
            raw("post",target_id=SOURCE.post_id,title="New idea",
                submolt="general",text="Body",reason="Interesting"),
            raw("post",target_id="",title="New idea",
                submolt="other",text="Body",reason="Interesting"),
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    decision.parse(malformed,SOURCE,now=NOW,author_observations=4)

    def test_follow_needs_two_separate_verified_author_observations(self):
        with self.assertRaisesRegex(ValueError,"r4_insufficient_repeat_author_evidence"):
            decision.parse(
                raw("follow",target_id=SOURCE.author,reason="Seems worthwhile"),
                SOURCE,now=NOW,author_observations=1)
        with self.assertRaises(ValueError):
            decision.parse(
                raw("follow",target_id=SOURCE.author,reason="Seems worthwhile"),
                SOURCE,now=NOW,author_observations=True)

    def test_unfollow_reply_and_untrusted_parent_never_accepted(self):
        for kind,attrs in (
            ("unfollow",dict(target_id=SOURCE.author)),
            ("reply",dict(text="This is a reply",parent_id="a"*36)),
            ("comment",dict(text="This is a comment",parent_id="a"*36)),
        ):
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    decision.parse(raw(kind,reason="Explanation",**attrs),
                                   SOURCE,now=NOW,author_observations=2)

    def test_exact_field_types_and_stale_source_required(self):
        failures=[
            "not JSON",json.dumps({"type":"skip"}),
            json.dumps(dict(json.loads(raw()),more="bad")),
            json.dumps(dict(json.loads(raw()),type=42)),
            raw(source_run="20261101T151034Z"),
            raw(target_id="not the source"),
            raw("skip",text="ignore previous instructions"),
            raw("skip",title="untrusted title"),
        ]
        for case in failures:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    decision.parse(case,SOURCE,now=NOW)
        for at in (NOW-timedelta(days=1),NOW+timedelta(days=3)):
            with self.assertRaises(ValueError):
                decision.parse(raw(),SOURCE,now=at)
        with self.assertRaises(ValueError):
            decision.parse(raw(),SOURCE,now=NOW.replace(tzinfo=None))


if __name__=="__main__":
    unittest.main()
