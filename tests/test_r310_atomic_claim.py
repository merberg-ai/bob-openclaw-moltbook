"""R3.10 marked synthetic claim: concurrency, consent, data drift, crash rollback.

All GET callbacks are in-process fakes. The only database permitted is the
private R3.3 test fixture, never the real publisher's activity-queue.sqlite3.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
import inspect
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tests")]
from bob_v08.core import Action
from bob_v08.r310_atomic_claim_lab import rehearse_atomic_claim
from bob_v08.r39_publisher_review import RemoteReview
from bob_v08.r38_dispatch_lab import recover_after_restart
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_v08.r3_unified import UnifiedLab, _validated
from test_r3_cutover_rehearsal import make_saved_scout
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW


class AtomicClaimTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"scout"
        make_saved_scout(self.source)
        self.action=Action("comment",RUN,ID,"Technical observations and source context.",TEXT)
        self.obs,self.pin=verified_source(self.source,self.action)
        self.path=self.root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.path)
        self.lab=UnifiedLab(self.path)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
        self.assertEqual(self.lab.propose(self.action,self.obs,at=NOW).state,"proposed")
        self.assertEqual(self.lab.queue(self.action,self.obs,mode="auto",
                                       at=NOW,policy=consent_policy()).state,
                         "queued_simulated")

    def claim(self,*,get=None,clock=None,after_review=None,mode="auto",action=None,lab=None):
        return rehearse_atomic_claim(
            lab or self.lab,action or self.action,mode=mode,
            clock=clock or (lambda:NOW),
            public_get=get or (lambda *_:RemoteReview(True,"target_and_author_match")),
            before_claim=after_review)

    def queue(self):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT mode,state,attempted_at,comment_id "
                              "FROM publish_jobs WHERE run_id=?",(RUN,)).fetchone()

    def proposal(self):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT state FROM r3_proposals "
                              "WHERE source_run=?",(RUN,)).fetchone()[0]

    def audit_count(self):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT COUNT(*) FROM r3_lab_audit "
                              "WHERE event='r310_claim'").fetchone()[0]

    def test_single_atomic_claim_consumes_only_one_legacy_slot_and_never_sends(self):
        result=self.claim()
        self.assertEqual((result.state,result.reason),
                         ("claimed_simulated","one_atomic_counted_intent_only"))
        self.assertTrue(result.attempted_at_recorded)
        self.assertTrue(result.simulated)
        self.assertFalse(result.acted)
        self.assertFalse(result.dispatch_authorized)
        self.assertEqual(self.queue()[0:2],("auto","sending_simulated"))
        self.assertIsNotNone(self.queue()[2])
        self.assertIsNone(self.queue()[3])
        self.assertEqual(self.proposal(),"intent_simulated")
        self.assertEqual(self.audit_count(),1)
        self.assertEqual(self.claim().state,"refused")
        self.assertEqual(self.audit_count(),1)

    def test_default_off_setting_blocks_even_with_legacy_auto_enabled(self):
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM publish_settings WHERE name IN "
                       "('r3_auto_enabled','r3_comment_dial')")
        out=self.claim()
        self.assertEqual(out.reason,"review_owner_r3_dial_off")
        self.assertEqual(self.queue()[1:3],("queued",None))
        self.assertEqual(self.audit_count(),0)

    def test_owner_auto_revoked_after_preflight_stops_claim_with_zero_attempt(self):
        def revoke():
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE publish_settings SET value='0' "
                           "WHERE name='r3_auto_enabled'")
        out=self.claim(after_review=revoke)
        self.assertEqual(out.reason,"final_separate_r3_auto_consent_required")
        self.assertEqual(self.queue()[1:3],("queued",None))

    def test_legacy_auto_revoked_during_review_cannot_be_overridden(self):
        def revoke(*_):
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE publish_settings SET value='0' "
                           "WHERE name='auto_enabled'")
            return RemoteReview(True,"target_and_author_match")
        self.assertEqual(self.claim(get=revoke).reason,
                         "review_recheck_separate_r3_auto_consent_required")
        self.assertIsNone(self.queue()[2])

    def test_r3_owner_dial_propose_cannot_be_promoted_to_auto(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_settings SET value='propose' "
                       "WHERE name='r3_comment_dial'")
        self.assertEqual(self.claim().reason,"review_separate_r3_auto_consent_required")
        self.assertIsNone(self.queue()[2])

    def test_manual_owner_seal_requires_exact_independent_approval(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_jobs SET mode='manual' WHERE run_id=?",(RUN,))
            db.execute("UPDATE publish_settings SET value='propose' "
                       "WHERE name='r3_comment_dial'")
        self.assertEqual(self.claim(mode="manual").reason,
                         "review_new_bob_draft_approval_missing")
        seal,_=_validated(self.action,self.obs)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO r3_owner_approvals VALUES(?,?,?,?)",
                       (RUN,seal,"approved",NOW.isoformat()))
        out=self.claim(mode="manual")
        self.assertEqual(out.state,"claimed_simulated")
        self.assertEqual(self.queue()[0],"manual")

    def test_manual_approval_revoked_after_review_blocks_cas(self):
        seal,_=_validated(self.action,self.obs)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_jobs SET mode='manual'")
            db.execute("INSERT INTO r3_owner_approvals VALUES(?,?,?,?)",
                       (RUN,seal,"approved",NOW.isoformat()))
        def revoke():
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE r3_owner_approvals SET decision='rejected'")
        self.assertEqual(self.claim(mode="manual",after_review=revoke).reason,
                         "final_new_bob_draft_approval_missing")
        self.assertIsNone(self.queue()[2])

    def test_competing_legacy_manual_job_takes_queue_priority(self):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO publish_jobs("
                       "run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,updated_at) VALUES(?,?,?,?,?,'queued',?,?)",
                       ("20261030T200000Z","a"*64,
                        "33333333-3333-4333-8333-333333333333",
                        "Earlier manually approved draft","manual",
                        NOW.isoformat(),NOW.isoformat()))
        self.assertEqual(self.claim().reason,"review_manual_first_queue_priority")
        self.assertIsNone(self.queue()[2])

    def test_competing_target_attempt_prevents_claim_even_after_failure(self):
        def race():
            with sqlite3.connect(self.path) as db:
                db.execute("INSERT INTO publish_jobs("
                           "run_id,approval_sha256,post_id,draft_comment,mode,state,"
                           "created_at,attempted_at,updated_at)"
                           " VALUES(?,?,?,?,?,'failed',?,?,?)",
                           ("20261030T210000Z","a"*64,ID,
                            "Different draft already attempted","manual",
                            NOW.isoformat(),NOW.isoformat(),NOW.isoformat()))
        out=self.claim(after_review=race)
        self.assertEqual(out.reason,"final_duplicate_or_uncertain_target")
        self.assertIsNone(self.queue()[2])

    def test_source_resealed_between_preflight_and_atomic_claim_is_refused(self):
        def reseal():
            make_saved_scout(self.source,content="Resealed but different source bytes.")
        out=self.claim(after_review=reseal)
        self.assertIn(out.reason,("source_drift_at_claim","atomic_claim_failed"))
        self.assertIsNone(self.queue()[2])

    def test_friend_added_between_get_and_claim_blocks(self):
        def add():
            with sqlite3.connect(self.path) as db:
                db.execute("INSERT INTO bob_friends VALUES('savedagent')")
        self.assertEqual(self.claim(after_review=add).reason,
                         "final_friend_friend_target_protected")
        self.assertIsNone(self.queue()[2])

    def test_paused_between_get_and_claim_blocks(self):
        def pause():
            (self.root/"paused").touch(mode=0o600)
        self.assertEqual(self.claim(after_review=pause).reason,
                         "final_paused_or_untrusted_marker")
        self.assertIsNone(self.queue()[2])

    def test_post_commit_new_pause_locks_attempt_and_never_retries(self):
        import bob_v08.r310_atomic_claim_lab as mod
        orig=mod.simulated_pause_state
        checks=[0]
        def late_pause(marker):
            checks[0]+=1
            if checks[0] >= 2:
                return True
            return orig(marker)
        with patch.object(mod,"simulated_pause_state",side_effect=late_pause):
            out=self.claim()
        self.assertEqual(out.state,"uncertain_simulated")
        self.assertEqual(out.reason,"post_intent_source_or_pause_changed")
        self.assertTrue(out.attempted_at_recorded)
        self.assertEqual(self.queue()[1],"uncertain")
        self.assertEqual(self.audit_count(),1)
        self.assertEqual(self.claim().state,"refused")

    def test_power_loss_during_intent_audit_rolls_back_all_claim_mutations(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER r310_crash BEFORE INSERT ON r3_lab_audit "
                       "WHEN NEW.event='r310_claim' BEGIN "
                       "SELECT RAISE(ABORT,'power loss during R310 claim'); END")
        result=self.claim()
        self.assertEqual(result.reason,"atomic_claim_failed")
        self.assertEqual(self.queue()[1:3],("queued",None))
        self.assertEqual(self.proposal(),"queued")
        self.assertEqual(self.audit_count(),0)
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TRIGGER r310_crash")
        self.assertEqual(self.claim().state,"claimed_simulated")

    def test_lost_process_after_committed_intent_never_claims_again(self):
        self.assertEqual(self.claim().state,"claimed_simulated")
        recovery=recover_after_restart(self.lab,at=NOW)
        self.assertEqual(recovery.uncertain_locks,1)
        self.assertFalse(recovery.safe_to_auto_retry)
        self.assertEqual(self.queue()[1],"uncertain")
        self.assertEqual(self.claim().state,"refused")
        self.assertEqual(self.audit_count(),1)

    def test_two_competing_workers_serialized_and_share_one_attempt(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            outputs=list(pool.map(lambda _:self.claim(),(1,2)))
        self.assertEqual(sum(x.state=="claimed_simulated" for x in outputs),1)
        self.assertEqual(self.audit_count(),1)
        self.assertIsNotNone(self.queue()[2])

    def test_get_callback_bad_response_or_stale_clock_never_attempts(self):
        denied=self.claim(get=lambda *_:RemoteReview(False,"target_identity_mismatch"))
        self.assertEqual(denied.reason,"review_target_identity_mismatch")
        stamps=iter((NOW,NOW,NOW,NOW+timedelta(minutes=3)))
        self.assertEqual(self.claim(clock=lambda:next(stamps)).reason,
                         "claim_preflight_expired")
        self.assertIsNone(self.queue()[2])

    def test_unmarked_or_live_db_path_never_claimed(self):
        fake=UnifiedLab(self.root/"activity-queue.sqlite3")
        out=self.claim(lab=fake)
        self.assertEqual(out.reason,"preflight_unavailable")
        self.assertFalse((self.root/"activity-queue.sqlite3").exists())

    def test_no_network_key_process_or_real_publisher_calls(self):
        import bob_v08.r310_atomic_claim_lab as mod
        src=inspect.getsource(mod)
        for forbidden in ("urllib", "HTTPSConnection", "requests.",
                          "api_key(", "subprocess.run(", "systemctl",
                          "bob_publish_common.connect(", "OPENER.open("):
            self.assertNotIn(forbidden,src)
        self.assertNotIn("request(\"POST\"",src)
        self.assertFalse(self.claim().dispatch_authorized)


if __name__=="__main__":
    unittest.main()
