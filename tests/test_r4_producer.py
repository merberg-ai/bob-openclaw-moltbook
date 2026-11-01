"""R4 future one-shot OpenClaw producer: synthetic host only, never POST."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src/lib/bob")]
from bob_v08.evidence import read_observation
import bob_r4_producer as producer
import bob_r4_ledger as ledger

RUN="20261101T151033Z"
POST="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
NOW=datetime(2026,11,1,16,20,tzinfo=timezone.utc)


class R4ProducerTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r4-producer-test-")
        self.addCleanup(temp.cleanup)
        home=Path(temp.name)
        self.saved=home/".config"/"moltbook"
        self.saved.mkdir(parents=True,mode=0o700)
        raw=json.dumps(
            {"posts":[{"id":POST,"author":"Test_Agent","title":"Synthetic",
                       "content":"A harmless test source."}]},sort_keys=True).encode()
        digest=hashlib.sha256(raw).hexdigest()
        draft="an old synthetic draft"
        obj={
            "schema":2,"run_id":RUN,
            "snapshot_file":"scout-feed-"+RUN+".json",
            "snapshot_sha256":digest,"chosen_post_id":POST,
            "draft_comment":draft,
            "draft_sha256":hashlib.sha256(draft.encode()).hexdigest(),
            "approval_sha256":hashlib.sha256(
                (POST+"\n"+draft+"\n"+digest).encode()).hexdigest()
        }
        (self.saved/("scout-feed-"+RUN+".json")).write_bytes(raw)
        (self.saved/("scout-result-"+RUN+".json")).write_text(json.dumps(obj))
        self.observation=read_observation(self.saved,RUN)
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
        self.db.execute("INSERT INTO publish_settings VALUES('r4_mode_upvote','propose')")
        self.db.execute("INSERT INTO publish_settings VALUES('r4_global_pause','0')")
        @contextmanager
        def fake_conn():
            yield self.db
        for ctx in (
            patch("bob_r313d_package.load_verified",
                  return_value="verified_registry_archive"),
            patch("bob_r313d_owner.trusted_manager_boundary",
                  return_value=True),
            patch("bob_v08.evidence.latest_observations",
                  return_value=(self.observation,)),
            patch.object(producer,"connect",fake_conn),
            patch.object(producer,"DATA",self.saved),
            patch.object(producer.Path,"home",return_value=home),
            patch.object(producer.os,"geteuid",return_value=1001),
            patch.object(producer.pwd,"getpwuid",
                         return_value=SimpleNamespace(pw_dir=str(home))),
        ):
            ctx.start()
            self.addCleanup(ctx.stop)

    def decision(self,kind="upvote",**changes):
        obj={"type":kind,"source_run":RUN,"target_id":POST,
             "reason":"A specific useful synthesis" if kind!="skip" else "",
             "text":"","title":"","submolt":"","parent_id":""}
        obj.update(changes)
        return json.dumps(obj)

    def once(self,model):
        return producer.run_one(model=model,clock=lambda:NOW)

    def test_one_genuine_proposal_not_publisher_queue(self):
        calls=[]
        result=self.once(lambda prompt,key:(
            calls.append((prompt,key)) or self.decision()))
        self.assertEqual(result.status,"proposed")
        self.assertEqual(result.reason,"private_owner_review_only")
        self.assertEqual(result.source_run,RUN)
        self.assertFalse(result.queued)
        self.assertFalse(result.attempted)
        self.assertFalse(result.dispatch_authorized)
        self.assertEqual(len(calls),1)
        self.assertIn("PRIVATE ACTION PROPOSAL",calls[0][0])
        self.assertEqual(ledger.recent(self.db,self.saved)[0]["state"],
                         "proposed")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)
        second=self.once(lambda *_:self.fail("reused consumed source"))
        self.assertEqual(second.status,"none")
        self.assertEqual(second.reason,"no_fresh_r4_source")

    def test_genuine_skip_is_durable_and_not_replayed(self):
        first=self.once(lambda *_:self.decision("skip"))
        self.assertEqual(first.status,"skipped")
        second=self.once(lambda *_:self.fail("do not repeat a saved skip"))
        self.assertEqual(second.status,"none")
        self.assertEqual(ledger.recent(self.db,self.saved)[0]["kind"],"skip")

    def test_off_and_pause_never_invoke_openclaw(self):
        self.db.execute("UPDATE publish_settings SET value='1' "
                        "WHERE name='r4_global_pause'")
        self.assertEqual(self.once(lambda *_:self.fail("paused")) .status,"none")
        self.db.execute("UPDATE publish_settings SET value='0' "
                        "WHERE name='r4_global_pause'")
        self.db.execute("UPDATE publish_settings SET value='off' "
                        "WHERE name='r4_mode_upvote'")
        self.assertEqual(self.once(lambda *_:self.fail("off")) .status,"none")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_social_decisions").fetchone()[0],0)

    def test_transport_or_model_contract_failure_does_not_consume_source(self):
        for bad in ("not JSON",self.decision(target_id="other"),"[]"):
            result=self.once(lambda *_:bad)
            self.assertEqual(result.status,"refused")
            self.assertEqual(result.reason,"r4_model_or_contract_unverified")
            self.assertEqual(self.db.execute(
                "SELECT COUNT(*) FROM r4_social_decisions").fetchone()[0],0)

    def test_live_source_changed_during_model_is_refused_without_skip(self):
        def tamper(*_):
            path=self.saved/("scout-feed-"+RUN+".json")
            path.write_bytes(path.read_bytes()+b" ")
            return self.decision()
        result=self.once(tamper)
        self.assertEqual(result.status,"refused")
        self.assertEqual(result.reason,"r4_source_or_owner_gate_changed")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r4_social_decisions").fetchone()[0],0)

    def test_r3_consumed_source_not_replayed_under_r4(self):
        self.db.execute("INSERT INTO r3_proposals VALUES(?,?)",(RUN,POST))
        result=self.once(lambda *_:self.fail("existing R3 source must not repeat"))
        self.assertEqual(result.status,"none")
        self.assertFalse(result.attempted)


if __name__=="__main__":
    unittest.main()
