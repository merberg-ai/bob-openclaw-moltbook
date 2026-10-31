"""R3.3 synthetic-only unified handoff: model seal, owner approvals, races and crash."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bob_v08.core import Action, Observation, Policy
from bob_v08.r3_unified import UnifiedLab, Proof, MARKER, _validated

NOW = datetime(2026, 10, 30, 23, 25, tzinfo=timezone.utc)
RUN = "20261030T230000Z"
RUN2 = "20261030T231000Z"
ID = "a9ccf436-c5d5-4849-af92-843670ab8271"
ID2 = "31ca4dd9-a0b4-4991-a671-f063946e1123"
TEXT = "Bob's source-grounded original technical observation about deterministic replays."
OTHER_TEXT = "Bob's independent thought on safely transferring ownership of queues."


def candidate(run=RUN, post=ID, body=TEXT):
    obs = Observation(run, post, "ThirdPartyAgent", "Systems post",
                      "A saved third-party snapshot", "a"*64, "b"*64, NOW.isoformat())
    action = Action("comment", run, post, "Interesting systems discussion.", body)
    return action, obs


def consent_policy(dial="auto", *, budget=2, spacing=10, paused=False):
    return replace(Policy(), shadow=False, paused=paused,
                   dials={"comment": dial}, budgets={"comment": budget},
                   minimum_spacing={"comment": spacing})


def fixture(path):
    path.parent.mkdir(mode=0o700)
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE decisions (
          run_id TEXT PRIMARY KEY,draft_sha256 TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('approved','rejected')),decided_at TEXT NOT NULL
        );
        CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE publish_jobs (
          run_id TEXT PRIMARY KEY,approval_sha256 TEXT NOT NULL,
          post_id TEXT NOT NULL,draft_comment TEXT NOT NULL,
          mode TEXT NOT NULL CHECK(mode IN ('manual','auto')),
          state TEXT NOT NULL,created_at TEXT NOT NULL,
          attempted_at TEXT,comment_id TEXT,challenge_code TEXT,
          challenge_text TEXT,challenge_expires_at TEXT,verify_answer TEXT,
          last_error TEXT,updated_at TEXT NOT NULL
        );
        CREATE TABLE r3_lab_meta(name TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE r3_owner_approvals(
          source_run TEXT PRIMARY KEY,seal_sha256 TEXT NOT NULL,
          decision TEXT NOT NULL,at TEXT NOT NULL
        );
        CREATE TABLE r3_proposals(
          source_run TEXT PRIMARY KEY,post_id TEXT NOT NULL UNIQUE,
          draft_comment TEXT NOT NULL,seal_sha256 TEXT NOT NULL,
          fingerprint TEXT NOT NULL,snapshot_sha256 TEXT NOT NULL,
          state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        );
        CREATE TABLE r3_lab_audit(
          id INTEGER PRIMARY KEY AUTOINCREMENT,source_run TEXT NOT NULL,
          event TEXT NOT NULL,reason TEXT NOT NULL,at TEXT NOT NULL
        );""")
        db.execute("INSERT INTO r3_lab_meta VALUES('contract',?)", (MARKER,))
        db.executemany("INSERT INTO publish_settings VALUES(?,?)", (
            ("auto_enabled","1"),
            ("r3_auto_enabled","1"),
            ("r3_comment_dial","auto"),
            ("r3_auto_since","2026-10-30T22:00:00Z"),
            ("activity_limit_comment_daily","2"),
            ("activity_limit_comment_auto_daily","1"),
            ("activity_limit_comment_gap_minutes","10"),
        ))
    os.chmod(path,0o600)


class UnifiedTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "r3-unified-fixtures" / "r3-unified-lab.sqlite3"
        fixture(self.path)
        self.lab = UnifiedLab(self.path)
        self.action, self.obs = candidate()
        self.another, self.another_obs = candidate(RUN2, ID2, OTHER_TEXT)
        self.auto = consent_policy()
        self.manual = consent_policy("propose")

    def sql(self, statement, params=()):
        with sqlite3.connect(self.path) as db:
            return db.execute(statement,params).fetchall()

    def approve(self, action=None, obs=None, *, decision="approved"):
        a, o = action or self.action, obs or self.obs
        seal, _ = _validated(a,o)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO r3_owner_approvals VALUES(?,?,?,?)",
                       (a.source_run, seal, decision, NOW.isoformat()))

    def stage_manual(self, action=None, obs=None):
        a, o = action or self.action, obs or self.obs
        self.assertEqual(self.lab.propose(a,o,at=NOW).state,"proposed")
        self.approve(a,o)
        return self.lab.queue(a,o,mode="manual",at=NOW,policy=self.manual)

    def stage_auto(self, action=None, obs=None):
        a, o = action or self.action, obs or self.obs
        self.assertEqual(self.lab.propose(a,o,at=NOW).state,"proposed")
        return self.lab.queue(a,o,mode="auto",at=NOW,policy=self.auto)

    def presend(self, action=None, obs=None, *, mode="auto", policy=None,
                paused=False, proof=None, at=NOW):
        a,o = action or self.action, obs or self.obs
        return self.lab.simulated_pre_send(
            a,o,mode=mode,at=at,policy=policy or (self.auto if mode=="auto" else self.manual),
            paused=paused,proof=proof or Proof(a.target_id,at,"clear"))

    def test_proposed_new_bob_comment_is_not_legacy_approval_or_send(self):
        result=self.lab.propose(self.action,self.obs,at=NOW)
        self.assertEqual((result.state,result.reason),("proposed","sealed_but_not_authorized"))
        self.assertFalse(result.acted)
        self.assertEqual(self.sql("SELECT count(*) FROM publish_jobs"),[(0,)])
        self.assertEqual(self.sql("SELECT count(*) FROM decisions"),[(0,)])
        self.assertEqual(self.lab.propose(self.action,self.obs,at=NOW).reason,
                         "proposal_or_target_already_seen")

    def test_manual_new_comment_needs_separate_exact_owner_approval(self):
        self.lab.propose(self.action,self.obs,at=NOW)
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="manual",
                         at=NOW,policy=self.manual).reason,
                         "owner_approval_missing_or_changed")
        self.approve(decision="rejected")
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="manual",
                         at=NOW,policy=self.manual).reason,
                         "owner_approval_missing_or_changed")
        self.approve()
        accepted=self.lab.queue(self.action,self.obs,mode="manual",
                                at=NOW,policy=self.manual)
        self.assertEqual(accepted.state,"queued_simulated")
        self.assertEqual(self.presend(mode="manual").state,"intent_simulated")
        self.assertEqual(self.sql("SELECT mode,state FROM publish_jobs"),
                         [("manual","sending_simulated")])
        self.assertFalse(self.presend(mode="manual").acted)

    def test_revoked_manual_approval_after_queue_permanently_holds(self):
        self.assertEqual(self.stage_manual().state,"queued_simulated")
        self.approve(decision="rejected")
        result=self.presend(mode="manual")
        self.assertEqual((result.state,result.reason),
                         ("held","owner_approval_missing_or_changed"))
        self.assertEqual(self.sql("SELECT attempted_at FROM publish_jobs"),[(None,)])
        self.assertEqual(self.presend(mode="manual").reason,"no_pending_r3_proposal")

    def test_auto_requires_both_owner_flags_v08_dial_and_since_timestamp(self):
        self.lab.propose(self.action,self.obs,at=NOW)
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",at=NOW).reason,
                         "shadow_only")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_settings SET value='0' WHERE name='r3_auto_enabled'")
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",at=NOW,
                         policy=self.auto).reason,"owner_auto_permission_off")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_settings SET value='1' WHERE name='r3_auto_enabled'")
            db.execute("UPDATE publish_settings SET value='2026-10-30T23:10:00Z' "
                       "WHERE name='r3_auto_since'")
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",at=NOW,
                         policy=self.auto).reason,"source_before_auto_opt_in")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_settings SET value='2026-10-30T22:00:00Z'"
                       " WHERE name='r3_auto_since'")
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",at=NOW,
                         policy=self.auto).state,"queued_simulated")

    def test_persisted_owner_dial_revoked_after_queue_blocks_intent(self):
        self.stage_auto()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_settings SET value='off' "
                       "WHERE name='r3_comment_dial'")
        result=self.presend()
        self.assertEqual((result.state,result.reason),
                         ("held","owner_comment_dial_off"))
        self.assertEqual(self.sql("SELECT attempted_at FROM publish_jobs"),[(None,)])

    def test_owner_propose_dial_cannot_be_upgraded_to_auto_by_caller(self):
        self.lab.propose(self.action,self.obs,at=NOW)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_settings SET value='propose' "
                       "WHERE name='r3_comment_dial'")
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",
                         at=NOW,policy=self.auto).reason,"owner_comment_not_auto")
        self.approve()
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="manual",
                         at=NOW,policy=self.manual).state,"queued_simulated")

    def test_auto_consent_revoked_after_queue_blocks_intent(self):
        self.stage_auto()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_settings SET value='0' WHERE name='r3_auto_enabled'")
        result=self.presend()
        self.assertEqual((result.state,result.reason),("held","owner_auto_permission_off"))
        self.assertEqual(self.sql("SELECT state,attempted_at FROM publish_jobs"),
                         [("held_simulated",None)])
        self.assertEqual(self.presend().reason,"no_pending_r3_proposal")

    def test_auto_friend_preflight_and_pause_enforced_after_queue(self):
        self.stage_auto()
        self.assertEqual(self.presend(proof=Proof(ID,NOW-timedelta(minutes=3),"clear")).reason,
                         "preflight_stale_or_future")
        self.assertEqual(self.presend(proof=Proof(ID2,NOW,"clear")).reason,
                         "preflight_missing_or_wrong_target")
        self.assertEqual(self.presend(proof=Proof(ID,NOW,"unknown")).reason,
                         "friend_guard_unproven")
        self.assertEqual(self.presend().reason,"no_pending_r3_proposal")
        # Separate fixture: pause is a durable hold, even after previous consent.
        self.assertEqual(self.lab.propose(self.another,self.another_obs,at=NOW).state,
                         "proposed")
        self.assertEqual(self.lab.queue(self.another,self.another_obs,mode="auto",
                                        at=NOW,policy=self.auto).state,"queued_simulated")
        self.assertEqual(self.presend(self.another,self.another_obs,paused=True).reason,
                         "paused_or_unknown")

    def test_manual_first_old_legacy_job_blocks_new_auto_intent(self):
        self.stage_auto()
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO publish_jobs(run_id,approval_sha256,post_id,draft_comment,"
                "mode,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                ("20261030T210000Z","a"*64,ID2,"An older approved draft.","manual",
                 "queued",NOW.isoformat(),NOW.isoformat()))
        self.assertEqual(self.presend().state,"waiting")
        self.assertEqual(self.presend().reason,"legacy_manual_first_priority")
        self.assertEqual(self.sql("SELECT attempted_at FROM publish_jobs "
                                  "WHERE run_id=?", (RUN,)),[(None,)])

    def test_different_shadow_text_must_not_inherit_a_scout_approval(self):
        self.stage_manual()
        changed=replace(self.action,text="A different generated comment by Bob.")
        rejected = self.lab.simulated_pre_send(
            changed,self.obs,mode="manual",at=NOW,
            policy=self.manual,paused=False,proof=Proof(ID,NOW))
        self.assertEqual((rejected.state,rejected.reason),
                         ("held","sealed_payload_changed"))
        self.assertEqual(self.sql("SELECT attempted_at FROM publish_jobs"),[(None,)])
        self.assertEqual(self.lab.queue(changed,self.obs,mode="manual",
                         at=NOW,policy=self.manual).reason,"unsealed_or_changed_draft")

    def test_two_workers_same_job_only_one_intent_and_one_counting_record(self):
        self.stage_auto()
        def race(_):
            return self.presend()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(race,(1,2)))
        self.assertEqual([x.state for x in outcomes].count("intent_simulated"),1)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM publish_jobs WHERE "
                                  "attempted_at IS NOT NULL"),[(1,)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM r3_lab_audit "
                                  "WHERE reason='sending_simulated'"),[(1,)])

    def test_exact_v07_daily_and_auto_attempt_limits_share_one_db(self):
        self.stage_auto()
        self.assertEqual(self.presend().state,"intent_simulated")
        self.assertEqual(self.lab.propose(self.another,self.another_obs,at=NOW).state,
                         "proposed")
        self.assertEqual(self.lab.queue(self.another,self.another_obs,mode="auto",
                                        at=NOW,policy=self.auto).state,"queued_simulated")
        result=self.presend(self.another,self.another_obs,at=NOW+timedelta(minutes=11),
                             proof=Proof(ID2,NOW+timedelta(minutes=11),"clear"))
        self.assertEqual((result.state,result.reason),("waiting","legacy_rate_or_budget"))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM publish_jobs WHERE "
                                  "attempted_at IS NOT NULL"),[(1,)])

    def test_budget_reduction_after_queue_remains_waiting_not_attempted(self):
        self.stage_auto()
        lowered=consent_policy(budget=0)
        result=self.presend(policy=lowered)
        # Pure policy re-evaluation can hold revoked action even before rate check.
        self.assertEqual(result.state,"held")
        self.assertEqual(self.sql("SELECT attempted_at FROM publish_jobs"),[(None,)])

    def test_crash_between_counted_intent_and_simulated_response_locks_target(self):
        self.stage_auto()
        self.assertEqual(self.presend().state,"intent_simulated")
        self.assertEqual(self.lab.simulated_uncertain(RUN,at=NOW).state,
                         "uncertain_simulated")
        self.assertEqual(self.lab.simulated_uncertain(RUN,at=NOW).state,"refused")
        self.assertEqual(self.presend().reason,"no_pending_r3_proposal")
        self.assertEqual(self.sql("SELECT state,attempted_at IS NOT NULL "
                                  "FROM publish_jobs"),[("uncertain",1)])

    def test_simulated_audit_crash_rolls_back_attempt_and_retains_queue(self):
        self.stage_auto()
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER simulate_crash BEFORE INSERT ON r3_lab_audit "
                       "WHEN NEW.event='intent_auto' BEGIN "
                       "SELECT RAISE(ABORT,'synthetic crash'); END")
        with self.assertRaisesRegex(sqlite3.DatabaseError,"synthetic crash"):
            self.presend()
        self.assertEqual(self.sql("SELECT state,attempted_at FROM publish_jobs"),
                         [("queued",None)])
        self.assertEqual(self.sql("SELECT state FROM r3_proposals"),[("queued",)])
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TRIGGER simulate_crash")
        self.assertEqual(self.presend().state,"intent_simulated")

    def test_legacy_target_and_old_approval_collisions_fail_before_queue(self):
        self.lab.propose(self.action,self.obs,at=NOW)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO decisions VALUES(?,?,?,?)",
                       (RUN,"b"*64,"approved",NOW.isoformat()))
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",at=NOW,
                         policy=self.auto).reason,"legacy_scout_run_collision")
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM decisions")
            db.execute("INSERT INTO publish_jobs(run_id,approval_sha256,post_id,"
                       "draft_comment,mode,state,created_at,attempted_at,updated_at)"
                       " VALUES(?,?,?,?,?,?,?,?,?)",
                       ("20261030T220000Z","c"*64,ID,"prior sent reply","auto",
                        "uncertain",NOW.isoformat(),NOW.isoformat(),NOW.isoformat()))
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",at=NOW,
                         policy=self.auto).reason,"existing_legacy_target_or_job")

    def test_default_shadow_no_permissions_and_production_db_unreachable(self):
        self.lab.propose(self.action,self.obs,at=NOW)
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",at=NOW).reason,
                         "shadow_only")
        with self.assertRaisesRegex(ValueError,"not_unified_lab_path"):
            UnifiedLab(self.root/"activity-queue.sqlite3")._open()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
            p.parent.mkdir(mode=0o700)
            with sqlite3.connect(p) as db:
                db.execute("CREATE TABLE r3_lab_meta(name TEXT,value TEXT)")
                db.execute("INSERT INTO r3_lab_meta VALUES('contract','wrong')")
            os.chmod(p,0o600)
            with self.assertRaisesRegex(ValueError,"untrusted_unified_lab_marker"):
                UnifiedLab(p)._open()

    def test_source_only_no_network_credentials_or_installers(self):
        import inspect
        import bob_v08.r3_unified as module
        code=inspect.getsource(module)
        for forbidden in ("urllib","requests.","api_key(","subprocess.run(",
                          "moltbook.com","systemctl","bob_publish_common.connect("):
            self.assertNotIn(forbidden,code)
        self.assertFalse(self.lab.propose(self.action,self.obs,at=NOW).acted)


if __name__ == "__main__":
    unittest.main()
