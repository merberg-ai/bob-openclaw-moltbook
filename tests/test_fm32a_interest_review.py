"""FM3.2a: local, source-verified Scout WHY interest proposals.

Only saved operator-curated friend records, no network or new model calls.
Exercise the existing six-field dashboard POST contract and publication boundary.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_publish_common as common
import bob_friends as friends
import bob_friend_scout as scout

RID="20261029T214411Z"
PID="01234567-89ab-cdef-0123-456789abcdef"


def field_values():
    return dict(display_name="Saved Friend",relationship="friend",
                interests="PRIVATE interest notes not for the model",
                notes="PRIVATE contact notes remain offline")


class InterestsTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.path=self.root/"queue.sqlite3"
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT)")
            db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                       "at TEXT,kind TEXT,details TEXT)")
            self.ident=friends.create(db,"FriendOne",field_values())
        for attr,obj in (("DATA",self.root),("DB",self.path)):
            mocked=patch.object(common,attr,obj)
            mocked.start()
            self.addCleanup(mocked.stop)
        self.make_record()

    def db(self):
        return sqlite3.connect(self.path)

    def friend(self):
        with self.db() as db:
            return friends._get(db,self.ident)

    def make_record(self,*,why="I want to learn how other agents revise beliefs.",
                    author="FriendOne"):
        feed={"posts":[{"id":PID,"author":author,"title":"Memory and beliefs",
                        "content":"An actual public discussion"}]}
        raw=json.dumps(feed).encode()
        (self.root/("scout-feed-"+RID+".json")).write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest()
        draft="I wonder what would change my mind."
        rec=dict(schema=2,run_id=RID,status="pending",chosen_post_id=PID,
                 chosen_title="Memory and beliefs",chosen_author=author,why=why,
                 snapshot_file="scout-feed-"+RID+".json",snapshot_sha256=digest,
                 draft_comment=draft,draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),
                 approval_sha256=hashlib.sha256(
                     (PID+"\n"+draft+"\n"+digest).encode()).hexdigest())
        (self.root/("scout-result-"+RID+".json")).write_text(json.dumps(rec))
        return rec

    def stage_form(self):
        item=self.friend()
        return dict(csrf="test",operation="interest_stage",
                    friend_id=item["id"],friend_sha=item["sha256"],
                    run_id=RID,post_id=PID)

    def review_form(self,item,decision="approve",reason=""):
        return dict(csrf="test",operation="interest_review",id=item["id"],
                    expected_sha=item["sha256"],decision=decision,reason=reason)

    def stage(self):
        with self.db() as db:
            scout.change(db,self.stage_form())
            return scout.interest_rows(db)[0]

    def test_stage_has_verified_provenance_and_no_private_notes(self):
        item=self.stage()
        self.assertEqual(item["status"],"pending")
        self.assertEqual(item["run_id"],RID)
        self.assertEqual(item["post_id"],PID)
        self.assertIn("revise beliefs",item["idea"])
        self.assertNotIn("PRIVATE",str(item))
        with self.db() as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM bob_friend_interest_history").fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM publish_settings").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM bob_friend_watch_prefs").fetchone()[0],0) if (
                db.execute("SELECT 1 FROM sqlite_master WHERE name='bob_friend_watch_prefs'").fetchone()) else None
            html=scout.page(db,"test",lambda title,body,path:body,[common.load_record(RID)])
            self.assertIn("Tentative interests",html)
            self.assertIn('name="operation" value="interest_review"',html)
            self.assertIn("I want to learn",html)
            self.assertNotIn("PRIVATE contact notes",html)
            self.assertIn("Publication boundary",html)

    def test_replay_and_extra_form_fields_are_denied(self):
        self.stage()
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"already staged"):
                scout.change(db,self.stage_form())
            with self.assertRaisesRegex(ValueError,"Invalid interest form"):
                scout.change(db,{**self.stage_form(),"unexpected":"x"})
            with self.assertRaisesRegex(ValueError,"source unavailable or changed"):
                scout.change(db,{**self.stage_form(),"post_id":"not-a-post"})
            self.assertEqual(len(scout.interest_rows(db)),1)

    def test_digest_review_and_reversible_history(self):
        old=self.stage()
        with self.db() as db:
            self.assertEqual(scout.change(db,self.review_form(old,"approve","Good question")),
                             "approved")
            with self.assertRaisesRegex(ValueError,"changed; reload"):
                scout.change(db,self.review_form(old,"reject"))
            approved=scout.interest_rows(db)[0]
            self.assertEqual(approved["status"],"approved")
            self.assertEqual(approved["review_reason"],"Good question")
            self.assertEqual(scout.change(db,self.review_form(approved,"reopen")),"pending")
            pending=scout.interest_rows(db)[0]
            self.assertEqual(scout.change(db,self.review_form(pending,"reject")),"rejected")
            denied=scout.interest_rows(db)[0]
            self.assertEqual(scout.change(db,self.review_form(denied,"archive")),"archived")
            archived=scout.interest_rows(db)[0]
            self.assertEqual(scout.change(db,self.review_form(archived,"reopen")),"pending")
            self.assertEqual(db.execute(
                "SELECT count(*) FROM bob_friend_interest_history").fetchone()[0],6)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM publish_settings").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM bob_friends").fetchone()[0],1)

    def test_source_change_blocks_approval_and_reopening(self):
        pending=self.stage()
        self.make_record(why="A different opinion, silently rewritten.")
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"source unavailable"):
                scout.change(db,self.review_form(pending,"approve"))
            self.assertEqual(scout.change(db,self.review_form(pending,"archive")),"archived")
            archived=scout.interest_rows(db)[0]
            with self.assertRaisesRegex(ValueError,"source unavailable"):
                scout.change(db,self.review_form(archived,"reopen"))
            self.assertEqual(scout.interest_rows(db)[0]["status"],"archived")

    def test_tampered_snapshot_and_unrelated_author_block_staging(self):
        self.make_record(author="UnknownOther")
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"source unavailable"):
                scout.change(db,self.stage_form())
        self.make_record()
        (self.root/("scout-feed-"+RID+".json")).write_text('{"posts":[]}')
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"source unavailable"):
                scout.change(db,self.stage_form())
            self.assertEqual(scout.interest_rows(db),[])

    def test_friend_integrity_status_and_bad_review_action(self):
        friend=self.friend()
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"active saved friend"):
                scout.change(db,{**self.stage_form(),"friend_sha":"0"*64})
            friends.change(db,friend["id"],friend["sha256"],"mute")
            with self.assertRaisesRegex(ValueError,"active saved friend"):
                scout.change(db,self.stage_form())
        friend=self.friend()
        with self.db() as db:
            friends.change(db,friend["id"],friend["sha256"],"reactivate")
        item=self.stage()
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"Invalid interest form"):
                scout.change(db,self.review_form(item,"follow"))
            with self.assertRaisesRegex(ValueError,"0-240"):
                scout.change(db,self.review_form(item,"approve","x"*241))
            self.assertEqual(scout.interest_rows(db)[0]["status"],"pending")

    def test_untrusted_why_is_escaped_and_never_executed(self):
        rec=self.make_record(why="<img src=x onerror=alert(1)>")
        with self.db() as db:
            page=scout.page(db,"test",lambda title,body,path:body,[rec])
            self.assertIn("&lt;img",page)
            self.assertNotIn("<img src=x",page)
            self.assertIn("Stage tentative interest for review",page)


if __name__=="__main__":
    unittest.main()
