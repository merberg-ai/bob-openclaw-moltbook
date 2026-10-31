"""R3.8 inert publisher lifecycle: intent, receipt, crash, reboot, no replay."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import inspect
import json
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
from bob_v08.core import Action
from bob_v08.r38_dispatch_lab import (
    InertSink, SimulatedPowerLoss, simulate_dispatch, recover_after_restart,
)
from bob_v08.r3_unified import UnifiedLab
from bob_v08.r3_cutover_rehearsal import verified_source
from test_r3_cutover_rehearsal import make_saved_scout
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW


class InertDispatchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root/"scout"
        make_saved_scout(self.source)
        self.action = Action("comment", RUN, ID, "Technical discussion.", TEXT)
        observed,_ = verified_source(self.source,self.action)
        self.dbpath = self.root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.dbpath)
        self.lab = UnifiedLab(self.dbpath)
        self.pause = self.root/"paused"
        with sqlite3.connect(self.dbpath) as db:
            db.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
        self.assertEqual(self.lab.propose(self.action,observed,at=NOW).state,"proposed")
        self.assertEqual(self.lab.queue(self.action,observed,mode="auto",
                         at=NOW,policy=consent_policy()).state,"queued_simulated")

    def go(self, sink=None, *, failpoint="", after_intent=None, mode="auto"):
        if sink is None:
            sink = InertSink("ack")
        return simulate_dispatch(
            self.lab,self.source,self.action,mode=mode,
            pause_marker=self.pause,
            get_post=lambda pid:{"data":{"post":{"id":pid,"author":"SavedAgent"}}},
            clock=lambda:NOW,sink=sink,failpoint=failpoint,
            after_intent=after_intent)

    def row(self):
        with sqlite3.connect(self.dbpath) as db:
            return db.execute("SELECT state,attempted_at,comment_id "
                              "FROM publish_jobs WHERE run_id=?",(RUN,)).fetchone()

    def counts(self):
        with sqlite3.connect(self.dbpath) as db:
            return db.execute("SELECT COUNT(*) FROM r3_lab_audit WHERE "
                              "event='r38_receipt'").fetchone()[0]

    def test_acknowledged_is_simulated_and_not_replayed(self):
        sink=InertSink("ack")
        r=self.go(sink)
        self.assertEqual((r.state,r.reason),
                         ("acknowledged_simulated","synthetic_ack_only"))
        self.assertFalse(r.acted)
        self.assertFalse(r.dispatched_to_moltbook)
        self.assertEqual(len(sink.calls),1)
        self.assertEqual(self.row()[0],"acknowledged_simulated")
        self.assertEqual(self.row()[2],sink.comment_id)
        self.assertIsNotNone(self.row()[1])
        self.assertEqual(self.counts(),1)
        self.assertEqual(self.go(sink).state,"refused")
        self.assertEqual(len(sink.calls),1)
        self.assertEqual(recover_after_restart(self.lab,at=NOW).uncertain_locks,0)

    def test_timeout_is_ambiguous_and_permanently_locks(self):
        sink=InertSink("timeout")
        r=self.go(sink)
        self.assertEqual((r.state,r.reason),
                         ("uncertain_simulated","synthetic_transport_unknown"))
        self.assertIsNotNone(self.row()[1])
        self.assertEqual(len(sink.calls),1)
        self.assertEqual(self.go(sink).state,"refused")
        self.assertEqual(len(sink.calls),1)
        self.assertEqual(recover_after_restart(self.lab,at=NOW).uncertain_locks,0)

    def test_missing_ack_and_rejected_response_cannot_be_treated_as_success(self):
        for response in ("malformed","rejected"):
            with self.subTest(response=response):
                # Reset by using a second marked fixture per subtest.
                with tempfile.TemporaryDirectory() as root:
                    path=Path(root)/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
                    fixture(path)
                    lab=UnifiedLab(path)
                    obs,_=verified_source(self.source,self.action)
                    with sqlite3.connect(path) as db:
                        db.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
                    lab.propose(self.action,obs,at=NOW)
                    lab.queue(self.action,obs,mode="auto",at=NOW,policy=consent_policy())
                    sink=InertSink(response)
                    result=simulate_dispatch(
                        lab,self.source,self.action,mode="auto",
                        pause_marker=self.pause,
                        get_post=lambda pid:{"data":{"post":{"id":pid,"author":"SavedAgent"}}},
                        clock=lambda:NOW,sink=sink)
                    self.assertEqual(result.state,"uncertain_simulated")
                    self.assertEqual(len(sink.calls),1)
                    with sqlite3.connect(path) as db:
                        self.assertIsNone(db.execute(
                            "SELECT comment_id FROM publish_jobs").fetchone()[0])

    def test_challenge_requires_human_and_is_not_auto_solved(self):
        sink=InertSink("challenge")
        r=self.go(sink)
        self.assertEqual((r.state,r.reason),
                         ("awaiting_verification_simulated","human_verification_required"))
        self.assertEqual(len(sink.calls),1)
        self.assertEqual(self.go(sink).state,"refused")
        self.assertEqual(len(sink.calls),1)
        self.assertIsNotNone(self.row()[1])

    def test_crash_after_intent_before_sink_restarts_as_uncertain(self):
        sink=InertSink()
        with self.assertRaisesRegex(SimulatedPowerLoss,"after_durable_intent"):
            self.go(sink,failpoint="after_intent")
        self.assertEqual(len(sink.calls),0)
        self.assertEqual(self.row()[0],"sending_simulated")
        first=recover_after_restart(self.lab,at=NOW)
        self.assertEqual(first.uncertain_locks,1)
        self.assertFalse(first.safe_to_auto_retry)
        self.assertEqual(self.row()[0],"uncertain_simulated")
        self.assertEqual(recover_after_restart(self.lab,at=NOW).uncertain_locks,0)
        self.assertEqual(self.go(sink).state,"refused")
        self.assertEqual(len(sink.calls),0)

    def test_crash_after_sink_before_receipt_does_not_resend(self):
        sink=InertSink()
        with self.assertRaisesRegex(SimulatedPowerLoss,"after_inert_sink"):
            self.go(sink,failpoint="after_sink")
        self.assertEqual(len(sink.calls),1)
        self.assertEqual(self.row()[0],"sending_simulated")
        self.assertEqual(recover_after_restart(self.lab,at=NOW).uncertain_locks,1)
        self.assertEqual(self.row()[0],"uncertain_simulated")
        self.assertEqual(self.go(sink).state,"refused")
        self.assertEqual(len(sink.calls),1)

    def test_revoke_auto_setting_after_durable_intent_never_fires_sink(self):
        def revoke():
            with sqlite3.connect(self.dbpath) as db:
                db.execute("UPDATE publish_settings SET value='0' WHERE name='r3_auto_enabled'")
        sink=InertSink()
        r=self.go(sink,after_intent=revoke)
        self.assertEqual(r.state,"uncertain_simulated")
        self.assertEqual(r.reason,"barrier_auto_consent_revoked")
        self.assertEqual(len(sink.calls),0)
        self.assertIsNotNone(self.row()[1])
        self.assertEqual(self.go(sink).state,"refused")

    def test_pause_after_intent_prevents_even_inert_sink(self):
        def pause():
            self.pause.touch(mode=0o600)
        sink=InertSink()
        r=self.go(sink,after_intent=pause)
        self.assertEqual(r.reason,"barrier_paused_at_dispatch_barrier")
        self.assertEqual(len(sink.calls),0)
        self.assertEqual(self.row()[0],"uncertain_simulated")

    def test_new_friend_after_intent_prevents_sink(self):
        def save_friend():
            with sqlite3.connect(self.dbpath) as db:
                db.execute("INSERT INTO bob_friends VALUES('savedagent')")
        sink=InertSink()
        r=self.go(sink,after_intent=save_friend)
        self.assertEqual(r.reason,"barrier_friend_target_protected")
        self.assertEqual(len(sink.calls),0)

    def test_source_changed_after_intent_prevents_sink(self):
        def corrupt():
            (self.source/("scout-feed-"+RUN+".json")).write_text("{}",encoding="utf-8")
        sink=InertSink()
        r=self.go(sink,after_intent=corrupt)
        self.assertEqual(r.reason,"barrier_source_changed_after_intent")
        self.assertEqual(len(sink.calls),0)

    def test_budget_decreased_after_intent_cannot_be_ignored(self):
        def reduce():
            with sqlite3.connect(self.dbpath) as db:
                db.execute("UPDATE publish_settings SET value='0' "
                           "WHERE name='activity_limit_comment_auto_daily'")
        sink=InertSink()
        r=self.go(sink,after_intent=reduce)
        self.assertEqual(r.reason,"barrier_budget_reduced_after_intent")
        self.assertEqual(len(sink.calls),0)

    def test_exact_one_inert_sink_call_under_two_workers(self):
        sink=InertSink()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(lambda _:self.go(sink),(0,1)))
        self.assertEqual(sum(x.state=="acknowledged_simulated" for x in results),1)
        self.assertEqual(len(sink.calls),1)
        self.assertEqual(self.counts(),1)

    def test_receipt_write_crash_retains_intent_for_recovery(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON r3_lab_audit "
                       "WHEN NEW.event='r38_receipt' BEGIN "
                       "SELECT RAISE(ABORT,'inert receipt disk error'); END")
        sink=InertSink()
        with self.assertRaisesRegex(sqlite3.DatabaseError,"inert receipt disk error"):
            self.go(sink)
        self.assertEqual(len(sink.calls),1)
        self.assertEqual(self.row()[0],"sending_simulated")
        with sqlite3.connect(self.dbpath) as db:
            db.execute("DROP TRIGGER fail_receipt")
        result=recover_after_restart(self.lab,at=NOW)
        self.assertEqual(result.uncertain_locks,1)
        self.assertEqual(self.go(sink).state,"refused")
        self.assertEqual(len(sink.calls),1)

    def test_restart_preserves_old_legacy_ambiguous_delivery_unchanged(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute("INSERT INTO publish_jobs("
                       "run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,attempted_at,updated_at)"
                       " VALUES(?,?,?,?,?,?,?,?,?)",
                       ("20261030T210000Z","a"*64,
                        "33333333-3333-4333-8333-333333333333",
                        "historic manual draft","manual","uncertain",
                        NOW.isoformat(),NOW.isoformat(),NOW.isoformat()))
        result=recover_after_restart(self.lab,at=NOW)
        self.assertEqual(result.preexisting_legacy_sends_for_review,1)
        self.assertFalse(result.safe_to_auto_retry)
        with sqlite3.connect(self.dbpath) as db:
            self.assertEqual(db.execute(
                "SELECT state,attempted_at IS NOT NULL FROM publish_jobs "
                "WHERE run_id='20261030T210000Z'").fetchone(),("uncertain",1))

    def test_recovery_does_not_repair_corrupt_synthetic_intent_by_resetting(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute("UPDATE publish_jobs SET state='sending_simulated',"
                       "attempted_at=NULL WHERE run_id=?",(RUN,))
        result=recover_after_restart(self.lab,at=NOW)
        self.assertEqual(result.invalid_synthetic_intents,1)
        self.assertFalse(result.safe_to_auto_retry)
        self.assertEqual(self.row()[0],"sending_simulated")

    def test_no_arbitrary_transport_can_be_substituted(self):
        class EvilSink(InertSink):
            def deliver(self, target, body):
                raise AssertionError("bad subclass should never be called")
        sink=EvilSink()
        result=self.go(sink)
        self.assertEqual(result.reason,"not_an_inert_sink")
        self.assertEqual(self.row()[0],"queued")

    def test_no_network_in_r38_dispatch_code(self):
        import bob_v08.r38_dispatch_lab as code
        body=inspect.getsource(code)
        for forbidden in ("urllib", "requests.", "OPENER.open(", "api_key(",
                          "subprocess.run(", "systemctl", "moltbook.com"):
            self.assertNotIn(forbidden,body)


if __name__=="__main__":
    unittest.main()
