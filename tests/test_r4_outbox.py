"""R4 future single-publisher outbox: private synthetic acceptance only.

No real host database or public network is touched. The original publisher
remains compiled Off for R4, even when a synthetic owner queues an upvote.
"""
from datetime import datetime,timedelta,timezone
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
import bob_r4_suggestions as suggestions
import bob_r4_outbox as outbox
import bob_r4_publisher_adapter as adapter

RUN="20261101T151033Z"
POST="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
NOW=datetime(2026,11,1,16,20,tzinfo=timezone.utc)


class R4OutboxTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r4-outbox-synthetic-")
        self.addCleanup(temp.cleanup)
        self.data=Path(temp.name)
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT);
          CREATE TABLE publish_events(id INTEGER PRIMARY KEY,at TEXT,
            kind TEXT,details TEXT);
          CREATE TABLE publish_jobs(
            run_id TEXT PRIMARY KEY,post_id TEXT,attempted_at TEXT,
            state TEXT);
          CREATE TABLE r3_proposals(source_run TEXT PRIMARY KEY,post_id TEXT);
        """)
        ledger.initialize(self.db)
        suggestions.initialize(self.db)
        outbox.initialize(self.db)
        self.db.execute("INSERT INTO publish_settings VALUES('r4_mode_upvote','propose')")
        self.db.execute("INSERT INTO publish_settings VALUES('r4_global_pause','0')")
        feed=json.dumps({"posts":[{
            "id":POST,"author":"Example_Thinker",
            "title":"Thinking about private reviews",
            "content":"Synthetic safe test record"}]},sort_keys=True).encode()
        sha=hashlib.sha256(feed).hexdigest()
        text="Unsent synthetic scout legacy draft"
        record={
            "schema":2,"run_id":RUN,"snapshot_file":"scout-feed-"+RUN+".json",
            "snapshot_sha256":sha,"chosen_post_id":POST,
            "chosen_author":"Example_Thinker","chosen_title":"Thinking",
            "status":"pending","draft_comment":text,
            "draft_sha256":hashlib.sha256(text.encode()).hexdigest(),
            "approval_sha256":hashlib.sha256(
                (POST+"\n"+text+"\n"+sha).encode()).hexdigest()}
        (self.data/("scout-feed-"+RUN+".json")).write_bytes(feed)
        (self.data/("scout-result-"+RUN+".json")).write_text(json.dumps(record))
        self.obs=read_observation(self.data,RUN)
        decision=Decision("upvote",RUN,POST,
                          "A specific insight worth reviewing","","","","")
        self.assertEqual(
            ledger.record(self.db,self.data,self.obs,decision,at=NOW),"proposed")
        proposal=ledger.recent(self.db,self.data)[0]
        self.seal=proposal["seal"]
        self.assertEqual(
            ledger.review(self.db,self.data,RUN,self.seal,
                "approve","APPROVE R4 "+RUN,trusted=True,at=NOW),
            "approved")

    def queue(self):
        return outbox.queue(self.db,self.data,RUN,self.seal,
                            "QUEUE R4 UPVOTE "+RUN,trusted=True,at=NOW)

    def test_owner_approval_alone_never_queues_or_dispatches(self):
        self.assertTrue(outbox.PUBLIC_DISPATCH_COMPILED_OFF)
        self.assertTrue(adapter.R4_REAL_DISPATCH_COMPILED_OFF)
        self.assertIsNone(adapter.maybe_r4_publisher_step(
            self.db,
            api_call=lambda *_:self.fail("no public R4 call"),
            credential_loader=lambda:self.fail("no R4 credential")))
        self.assertIsNone(outbox._head(self.db))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone(),(0,))

    def test_exact_seal_and_distinct_owner_queue_required(self):
        for seal,phrase,trusted in (
            ("0"*64,"QUEUE R4 UPVOTE "+RUN,True),
            (self.seal,"QUEUE R4 FOLLOW "+RUN,True),
            (self.seal,"QUEUE R4 UPVOTE "+RUN,False),
        ):
            with self.subTest(seal=seal,phrase=phrase,trusted=trusted):
                with self.assertRaises(ValueError):
                    outbox.queue(self.db,self.data,RUN,seal,phrase,
                                 trusted=trusted,at=NOW)
        self.assertEqual(self.queue(),"queued_no_public_send")
        with self.assertRaises(ValueError):
            self.queue()
        self.assertEqual(self.db.execute(
            "SELECT state,attempted_at FROM r4_action_outbox").fetchone(),
                         ("queued",None))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone(),(0,))

    def test_fake_upvote_intent_persisted_before_network_and_no_retry(self):
        self.queue()
        calls=[]
        def mocked_transport(method,path):
            calls.append((method,path,self.db.execute(
                "SELECT state,attempted_at FROM r4_action_outbox "
                "WHERE source_run=?",(RUN,)).fetchone()))
            return {"success":True}
        self.assertEqual(outbox.offline_rehearsal(
            self.db,self.data,at=NOW,post_callback=mocked_transport),
                         "acknowledged")
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][:2],("POST","/posts/"+POST+"/upvote"))
        self.assertEqual(calls[0][2][0],"attempting")
        self.assertIsNotNone(calls[0][2][1])
        self.assertEqual(outbox.offline_rehearsal(
            self.db,self.data,at=NOW,
            post_callback=lambda *_:self.fail("must not replay")),
            "no_queued_r4_action")
        self.assertEqual(self.db.execute(
            "SELECT state FROM r4_action_outbox").fetchone(),
                         ("acknowledged",))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone(),(0,))

    def test_timeout_and_unknown_response_are_uncertain_no_replay(self):
        self.queue()
        def timeout(*_):
            raise TimeoutError("simulated network ambiguity")
        self.assertEqual(outbox.offline_rehearsal(
            self.db,self.data,at=NOW,post_callback=timeout),"uncertain")
        self.assertEqual(outbox.offline_rehearsal(
            self.db,self.data,at=NOW,
            post_callback=lambda *_:self.fail("no auto retry")),
            "no_queued_r4_action")
        self.assertEqual(self.db.execute(
            "SELECT last_code FROM r4_action_outbox").fetchone(),
            ("outcome_uncertain",))

    def test_crash_after_counted_intent_recovers_without_second_call(self):
        self.queue()
        intent=outbox.reserve_once(self.db,self.data,at=NOW)
        self.assertEqual(intent["target"],POST)
        self.assertEqual(outbox.recover_uncertain(self.db,at=NOW),1)
        self.assertEqual(outbox.recover_uncertain(self.db,at=NOW),0)
        self.assertEqual(self.db.execute(
            "SELECT state FROM r4_action_outbox").fetchone(),
            ("uncertain",))
        with self.assertRaises(ValueError):
            self.queue()
        self.assertEqual(outbox.offline_rehearsal(
            self.db,self.data,at=NOW,
            post_callback=lambda *_:self.fail("no replay")),
            "no_queued_r4_action")

    def test_queue_can_cancel_before_attempt_not_after(self):
        self.queue()
        self.assertEqual(outbox.cancel(
            self.db,RUN,"CANCEL R4 "+RUN,trusted=True,at=NOW),"cancelled")
        with self.assertRaises(ValueError):
            outbox.cancel(self.db,RUN,"CANCEL R4 "+RUN,
                          trusted=True,at=NOW)
        self.assertIsNone(outbox._head(self.db))
        with self.assertRaises(ValueError):
            self.queue()

    def test_paused_revoked_or_consumed_legacy_target_holds_intent(self):
        self.queue()
        for field,value in (("r4_global_pause","1"),
                            ("r4_mode_upvote","off")):
            self.db.execute(
                "UPDATE publish_settings SET value=? WHERE name=?",
                (value,field))
            with self.assertRaises(ValueError):
                outbox.reserve_once(self.db,self.data,at=NOW)
            self.db.execute(
                "UPDATE publish_settings SET value=? WHERE name=?",
                ("0" if field=="r4_global_pause" else "propose",field))
            self.assertEqual(self.db.execute(
                "SELECT attempted_at FROM r4_action_outbox").fetchone(),(None,))
        self.db.execute(
            "INSERT INTO publish_jobs VALUES(?,?,?,?)",
            ("20261101T160000Z",POST,NOW.isoformat(),"published"))
        with self.assertRaisesRegex(ValueError,"r4_outbox_late_legacy_collision"):
            outbox.reserve_once(self.db,self.data,at=NOW)
        self.assertEqual(self.db.execute(
            "SELECT state FROM r4_action_outbox").fetchone(),("queued",))

    def test_source_tampering_and_legacy_queue_precedence(self):
        self.queue()
        self.db.execute(
            "INSERT INTO publish_jobs VALUES(?,?,?,?)",
            ("20261101T160000Z","fa2095bd-15cf-46e9-9bf0-8aa47bea6c5a",
             None,"queued"))
        with self.assertRaisesRegex(ValueError,"r4_outbox_legacy_queue_has_precedence"):
            outbox.reserve_once(self.db,self.data,at=NOW)
        self.db.execute("DELETE FROM publish_jobs")
        feed=self.data/("scout-feed-"+RUN+".json")
        feed.write_bytes(feed.read_bytes()+b" ")
        with self.assertRaises(ValueError):
            outbox.reserve_once(self.db,self.data,at=NOW)

    def test_rehearsal_refuses_persistent_database_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=sqlite3.connect(str(Path(tmp)/"do-not-touch.sqlite"))
            self.addCleanup(db.close)
            with self.assertRaisesRegex(ValueError,"rehearsal_requires_memory_db"):
                outbox.offline_rehearsal(
                    db,self.data,at=NOW,
                    post_callback=lambda *_:self.fail("not allowed"))

    def test_unknown_ack_is_not_independent_public_receipt(self):
        self.queue()
        self.assertEqual(outbox.offline_rehearsal(
            self.db,self.data,at=NOW,post_callback=lambda *_:{"ok":True}),
            "uncertain")
        self.assertEqual(self.db.execute(
            "SELECT state FROM r4_action_outbox").fetchone(),
            ("uncertain",))


if __name__=="__main__":
    unittest.main()
