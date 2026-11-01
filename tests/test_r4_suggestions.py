"""R4 Bob evidence suggestions and explicit PM2/FM handoff, entirely offline."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src/lib/bob")]
from bob_v08.evidence import read_observation
from bob_r4_decision import Decision
import bob_r4_ledger as ledger
import bob_r4_suggestions as suggest
import bob_publish_common as common
import bob_memory as memory
import bob_friend_discovery as discover

RUN="20261101T151033Z"
OTHER="20261101T152033Z"
POST="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
POST2="fa2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
AUTHOR="Interesting_Agent"
NOW=datetime(2026,11,1,16,20,tzinfo=timezone.utc)


class R4EvidenceSuggestionsTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="r4-suggest-scout-")
        self.addCleanup(tmp.cleanup)
        self.feed=Path(tmp.name)
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT);
          CREATE TABLE publish_events(id INTEGER PRIMARY KEY,at TEXT,
            kind TEXT,details TEXT);
          CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,post_id TEXT);
          CREATE TABLE r3_proposals(source_run TEXT PRIMARY KEY,post_id TEXT);
        """)
        ledger.initialize(self.db)
        suggest.initialize(self.db)
        memory.initialize(self.db)
        discover.initialize(self.db)
        self.assertTrue(suggest.schema_ready(self.db))
        self.db.execute("INSERT INTO publish_settings VALUES('r4_global_pause','0')")
        for action in ("upvote","follow"):
            self.db.execute("INSERT INTO publish_settings VALUES(?,?)",
                            ("r4_mode_"+action,"propose"))
        self.save(RUN,POST)
        self.save(OTHER,POST2)
        self.obs=read_observation(self.feed,RUN)

    def save(self,run,post):
        feed=json.dumps({
            "posts":[{"id":post,"author":AUTHOR,"title":"Thoughtful synthetic",
                      "content":"Mock text only; this is not a public post"}]},
            sort_keys=True).encode()
        snapshot=hashlib.sha256(feed).hexdigest()
        comment="Synthetic private Scout draft"
        record={
            "schema":2,"run_id":run,"chosen_post_id":post,
            "chosen_author":AUTHOR,"chosen_title":"Thoughtful synthetic",
            "snapshot_file":"scout-feed-"+run+".json",
            "snapshot_sha256":snapshot,"status":"pending",
            "draft_comment":comment,
            "draft_sha256":hashlib.sha256(comment.encode()).hexdigest(),
            "approval_sha256":hashlib.sha256(
                (post+"\n"+comment+"\n"+snapshot).encode()).hexdigest()
        }
        (self.feed/("scout-feed-"+run+".json")).write_bytes(feed)
        (self.feed/("scout-result-"+run+".json")).write_text(
            json.dumps(record))

    def record(self,kind="upvote",reason="Bob found a useful recurring pattern"):
        action=Decision(kind,RUN,AUTHOR if kind=="follow" else POST,
                        reason,"","","","")
        self.assertEqual(ledger.record(
            self.db,self.feed,self.obs,action,at=NOW),"proposed")
        return action

    def cards(self):
        return suggest.recent(self.db,self.feed)

    def decide(self,kind,operation="approve",seal=None):
        item=next(x for x in self.cards() if x["kind"]==kind)
        confirmation=operation.upper()+" R4 "+kind.upper()+" "+RUN
        return suggest.review(self.db,self.feed,RUN,kind,
                              seal or item["seal"],operation,confirmation,
                              trusted=True,at=NOW)

    def test_one_real_bob_decision_stages_one_sealed_memory_note(self):
        self.record()
        items=self.cards()
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]["kind"],"memory")
        self.assertEqual(items[0]["state"],"pending")
        self.assertEqual(items[0]["detail"],
                         "Bob found a useful recurring pattern")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bob_memories").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bob_friends").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)

    def test_memory_approval_creates_owner_reviewed_low_confidence_pm2_note(self):
        self.record()
        result=self.decide("memory")
        self.assertEqual(result["state"],"approved")
        self.assertEqual(result["destination"],"pm2_owner_memory")
        self.assertFalse(result["molbook_action_authorized"])
        row=self.db.execute(
            "SELECT id,title,content,category,confidence,source_kind,"
            "source_label FROM bob_memories").fetchone()
        self.assertEqual(row[0],result["applied_ref"])
        self.assertEqual(row[2],"Bob found a useful recurring pattern")
        self.assertEqual((row[3],row[4],row[5]),
                         ("opinion","low","operator"))
        self.assertIn(RUN,row[6])
        self.assertEqual(self.cards()[0]["state"],"approved")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)
        with self.assertRaises(ValueError):
            self.decide("memory")

    def test_follow_stages_both_memory_and_relationship_but_no_friend(self):
        self.record("follow")
        cards=self.cards()
        self.assertEqual({x["kind"] for x in cards},
                         {"memory","relationship"})
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bob_friends").fetchone()[0],0)
        # A separate owner review is still mandatory.
        with patch.object(common,"DATA",self.feed):
            result=self.decide("relationship")
        self.assertEqual(result["destination"],"fm_discovery_pending")
        self.assertFalse(result["molbook_action_authorized"])
        self.assertEqual(self.db.execute(
            "SELECT status,handle FROM bob_friend_candidates").fetchone(),
            ("pending",AUTHOR))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bob_friends").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)

    def test_rejection_is_terminal_without_pm2_or_fm_side_effect(self):
        self.record("follow")
        with patch.object(common,"DATA",self.feed):
            result=self.decide("relationship",operation="reject")
        self.assertEqual(result["destination"],"none")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bob_friend_candidates").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bob_memories").fetchone()[0],0)
        self.assertEqual(self.cards()[0]["state"],"pending")  # memory remains
        self.assertEqual({x["state"] for x in self.cards()},
                         {"pending","rejected"})

    def test_wrong_consent_seal_untrusted_owner_or_source_tamper_refused(self):
        self.record()
        item=self.cards()[0]
        for kwargs in (
            {"trusted":False,"confirmation":"APPROVE R4 MEMORY "+RUN},
            {"trusted":True,"confirmation":"APPROVE R4 FRIEND "+RUN},
            {"trusted":True,"seal":"f"*64,
             "confirmation":"APPROVE R4 MEMORY "+RUN},
        ):
            values=dict(trusted=True,seal=item["seal"],
                        confirmation="APPROVE R4 MEMORY "+RUN)
            values.update(kwargs)
            with self.assertRaises(ValueError):
                suggest.review(self.db,self.feed,RUN,"memory",
                               values["seal"],"approve",
                               values["confirmation"],trusted=values["trusted"],
                               at=NOW)
        source=self.feed/("scout-feed-"+RUN+".json")
        source.write_bytes(source.read_bytes()+b" ")
        self.assertEqual(self.cards(),[])
        with self.assertRaises(ValueError):
            self.decide_missing("memory",item["seal"])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bob_memories").fetchone()[0],0)

    def decide_missing(self,kind,seal):
        return suggest.review(
            self.db,self.feed,RUN,kind,seal,"approve",
            "APPROVE R4 "+kind.upper()+" "+RUN,trusted=True,at=NOW)

    def test_social_rejection_blocks_later_memory_acceptance(self):
        self.record()
        proposal=ledger.recent(self.db,self.feed)[0]
        self.assertEqual(ledger.review(
            self.db,self.feed,RUN,proposal["seal"],"reject",
            "REJECT R4 "+RUN,trusted=True,at=NOW),"rejected")
        with self.assertRaisesRegex(ValueError,
                                    "r4_parent_social_proposal_rejected"):
            self.decide("memory")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bob_memories").fetchone()[0],0)

    def test_partial_missing_schema_rolls_back_parent_r4_decision(self):
        self.db.execute("DROP TABLE r4_evidence_reviews")
        action=Decision("upvote",OTHER,POST2,
                        "Another genuinely specific interpretation","","","","")
        source=read_observation(self.feed,OTHER)
        with self.assertRaisesRegex(ValueError,"r4_suggestion_schema_not_installed"):
            ledger.record(self.db,self.feed,source,action,at=NOW)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_social_decisions").fetchone()[0],0)


if __name__=="__main__":
    unittest.main()
