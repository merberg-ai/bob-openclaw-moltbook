"""R4 full source-sealed private proposal ledger; synthetic saved Scout only.

All fixtures live in a temporary directory or in-memory SQLite, and no
Moltbook network, production user files, timer or publisher is touched.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src/lib/bob")]

from bob_v08.evidence import read_observation
import bob_r4_ledger as ledger
from bob_r4_decision import Decision,parse
from bob_r4_controls import set_mode

RUN="20261101T151033Z"
SECOND="20261101T152033Z"
POST="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
OTHER_POST="fa2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
NOW=datetime(2026,11,1,16,20,tzinfo=timezone.utc)
AUTHOR="Interesting_Agent"


def serialized(kind,run=RUN,target=POST,body="",reason="Original useful idea"):
    return Decision(kind,run,target,reason,body,"","","")


class R4LedgerTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r4-synthetic-scout-")
        self.addCleanup(temp.cleanup)
        self.directory=Path(temp.name)
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT);
          CREATE TABLE publish_events(id INTEGER PRIMARY KEY,at TEXT,
            kind TEXT,details TEXT);
          CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,post_id TEXT,
            attempted_at TEXT);
          CREATE TABLE r3_proposals(source_run TEXT PRIMARY KEY,post_id TEXT);
        """)
        ledger.initialize(self.db)
        self.assertTrue(ledger.schema_ready(self.db))
        self.save_run(RUN,POST)
        self.save_run(SECOND,OTHER_POST)
        self.obs=read_observation(self.directory,RUN)
        for mode in ("comment","upvote","follow","post"):
            self.db.execute(
                "INSERT INTO publish_settings VALUES(?,?)",
                ("r4_mode_"+mode,"propose"))
        self.db.execute("INSERT INTO publish_settings VALUES('r4_global_pause','0')")

    def save_run(self,run,post,author=AUTHOR):
        feed={"fetched_at":NOW.isoformat(),
              "posts":[{"id":post,"title":"Synthetic source","author":author,
                        "content":"This is a fake test post, not an instruction"}]}
        payload=json.dumps(feed,sort_keys=True).encode()
        digest=hashlib.sha256(payload).hexdigest()
        comment="synthetic legacy draft, never sent"
        document={"schema":2,"run_id":run,
                  "snapshot_file":"scout-feed-"+run+".json",
                  "snapshot_sha256":digest,
                  "chosen_post_id":post,"draft_comment":comment,
                  "draft_sha256":hashlib.sha256(comment.encode()).hexdigest(),
                  "approval_sha256":hashlib.sha256(
                    (post+"\n"+comment+"\n"+digest).encode()).hexdigest()}
        (self.directory/("scout-feed-"+run+".json")).write_bytes(payload)
        (self.directory/("scout-result-"+run+".json")).write_text(
            json.dumps(document))

    def record(self,decision,at=NOW):
        source=read_observation(self.directory,decision.source_run)
        return ledger.record(self.db,self.directory,source,decision,at=at)

    def test_schema_is_additive_and_does_not_change_old_history(self):
        before={name:self.db.execute("SELECT count(*) FROM "+name).fetchone()[0]
                for name in ("publish_jobs","r3_proposals","publish_events")}
        ledger.initialize(self.db)
        self.assertTrue(ledger.schema_ready(self.db))
        self.assertEqual(before,{name:self.db.execute(
            "SELECT count(*) FROM "+name).fetchone()[0]
            for name in before})
        self.assertEqual(ledger.recent(self.db,self.directory),[])

    def test_durable_skip_consumed_once_and_does_not_create_send(self):
        decision=serialized("skip",reason="")
        self.assertEqual(self.record(decision),"skipped")
        with self.assertRaisesRegex(ValueError,"r4_source_already_decided"):
            self.record(decision)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r3_proposals").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT event FROM r4_social_events").fetchall(),
            [("bob_skip",)])
        rows=ledger.recent(self.db,self.directory)
        self.assertEqual(rows[0]["kind"],"skip")
        self.assertFalse(rows[0]["approval_is_public_permission"])

    def test_owner_approved_private_proposal_not_queued_or_sent(self):
        decision=serialized("upvote",reason="A genuinely specific observation")
        self.assertEqual(self.record(decision),"proposed")
        item=ledger.recent(self.db,self.directory)[0]
        self.assertEqual(item["state"],"proposed")
        self.assertEqual(item["target"],POST)
        self.assertRegex(item["seal"],r"^[a-f0-9]{64}$")
        with self.assertRaisesRegex(ValueError,"r4_exact_review_phrase_required"):
            ledger.review(self.db,self.directory,RUN,item["seal"],
                          "approve","APPROVE R4 OTHER",trusted=True,at=NOW)
        self.assertEqual(ledger.review(
            self.db,self.directory,RUN,item["seal"],"approve",
            "APPROVE R4 "+RUN,trusted=True,at=NOW),"approved")
        after=ledger.recent(self.db,self.directory)[0]
        self.assertEqual(after["state"],"approved")
        self.assertFalse(after["queued"])
        self.assertFalse(after["attempted"])
        self.assertFalse(after["approval_is_public_permission"])
        with self.assertRaisesRegex(ValueError,"r4_review_seal_or_state_mismatch"):
            ledger.review(self.db,self.directory,RUN,item["seal"],"reject",
                          "REJECT R4 "+RUN,trusted=True,at=NOW)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT decision FROM r4_social_reviews").fetchone(),("approved",))

    def test_rejected_proposal_is_terminal(self):
        self.record(serialized("comment",body="Original synthetic reply"))
        seal=ledger.recent(self.db,self.directory)[0]["seal"]
        self.assertEqual(ledger.review(
            self.db,self.directory,RUN,seal,"reject",
            "REJECT R4 "+RUN,trusted=True,at=NOW),"rejected")
        self.assertEqual(ledger.recent(self.db,self.directory)[0]["state"],
                         "rejected")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)

    def test_pause_revocation_wrong_seal_and_old_source_fail(self):
        self.record(serialized("upvote"))
        correct=ledger.recent(self.db,self.directory)[0]["seal"]
        for value in ("0"*64,"X"*64,"",None):
            with self.subTest(seal=value):
                with self.assertRaises(ValueError):
                    ledger.review(self.db,self.directory,RUN,value,"approve",
                                  "APPROVE R4 "+RUN,trusted=True,at=NOW)
        with self.assertRaises(ValueError):
            ledger.review(self.db,self.directory,RUN,correct,"approve",
                          "APPROVE R4 "+RUN,trusted=False,at=NOW)
        self.db.execute("UPDATE publish_settings SET value='1' "
                        "WHERE name='r4_global_pause'")
        with self.assertRaisesRegex(ValueError,"r4_action_paused_or_revoked"):
            ledger.review(self.db,self.directory,RUN,correct,"approve",
                          "APPROVE R4 "+RUN,trusted=True,at=NOW)
        self.db.execute("UPDATE publish_settings SET value='0' "
                        "WHERE name='r4_global_pause'")
        self.db.execute("UPDATE publish_settings SET value='off' "
                        "WHERE name='r4_mode_upvote'")
        with self.assertRaisesRegex(ValueError,"r4_action_paused_or_revoked"):
            ledger.review(self.db,self.directory,RUN,correct,"approve",
                          "APPROVE R4 "+RUN,trusted=True,at=NOW)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_social_reviews").fetchone()[0],0)
        self.db.execute("UPDATE publish_settings SET value='propose' "
                        "WHERE name='r4_mode_upvote'")
        with self.assertRaisesRegex(ValueError,"r4_review_source_expired"):
            ledger.review(self.db,self.directory,RUN,correct,"approve",
                          "APPROVE R4 "+RUN,trusted=True,
                          at=NOW+timedelta(days=3))

    def test_changed_original_source_fails_closed_for_review_and_display(self):
        self.record(serialized("upvote"))
        item=ledger.recent(self.db,self.directory)[0]
        source_file=self.directory/("scout-feed-"+RUN+".json")
        source_file.write_text('{"posts":[]}')
        self.assertEqual(ledger.recent(self.db,self.directory),[])
        with self.assertRaises(ValueError):
            ledger.review(self.db,self.directory,RUN,item["seal"],"approve",
                          "APPROVE R4 "+RUN,trusted=True,at=NOW)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_social_reviews").fetchone()[0],0)

    def test_changed_saved_seal_or_raw_model_output_not_rendered(self):
        self.record(serialized("upvote"))
        self.db.execute("UPDATE r4_social_decisions SET decision_json='{}' "
                        "WHERE source_run=?",(RUN,))
        self.assertEqual(ledger.recent(self.db,self.directory),[])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)

    def test_follow_requires_two_real_saved_author_sources(self):
        d=serialized("follow",target=AUTHOR)
        self.assertEqual(self.record(d),"proposed")
        self.assertEqual(ledger.recent(self.db,self.directory)[0]["target"],
                         AUTHOR)
        with self.assertRaises(ValueError):
            self.record(serialized("follow",run=SECOND,target="A_Different_Agent"))
        # A forged second observation with the same post content but another
        # author is NOT sufficient for Bob to claim repeat interactions.
        fresh=SECOND+""
        self.db.execute("DELETE FROM r4_social_decisions")
        self.save_run(SECOND,OTHER_POST,author="Other_Agent")
        with self.assertRaisesRegex(ValueError,"r4_insufficient_repeat_author_evidence"):
            self.record(d)

    def test_duplicate_across_r3_or_legacy_consumed_source_refused(self):
        self.db.execute("INSERT INTO r3_proposals VALUES(?,?)",(RUN,POST))
        with self.assertRaisesRegex(ValueError,"r4_legacy_source_already_used"):
            self.record(serialized("upvote"))
        self.db.execute("DELETE FROM r3_proposals")
        self.db.execute("INSERT INTO publish_jobs VALUES(?,?,?)",
                        (SECOND,OTHER_POST,NOW.isoformat()))
        with self.assertRaisesRegex(ValueError,"r4_legacy_source_already_used"):
            self.record(serialized("upvote",run=SECOND,target=OTHER_POST))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_social_decisions").fetchone()[0],0)

    def test_mode_off_or_pause_refuses_new_records(self):
        d=serialized("upvote")
        self.db.execute("UPDATE publish_settings SET value='off' "
                        "WHERE name='r4_mode_upvote'")
        with self.assertRaisesRegex(ValueError,"r4_action_revoked"):
            self.record(d)
        self.db.execute("UPDATE publish_settings SET value='propose' "
                        "WHERE name='r4_mode_upvote'")
        self.db.execute("UPDATE publish_settings SET value='1' "
                        "WHERE name='r4_global_pause'")
        with self.assertRaisesRegex(ValueError,"r4_decisions_paused_or_off"):
            self.record(d)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_social_decisions").fetchone()[0],0)


if __name__=="__main__":
    unittest.main()
