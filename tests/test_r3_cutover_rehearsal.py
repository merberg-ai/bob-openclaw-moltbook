"""R3.4 cutover rehearsal: verified Scout bytes, owner dial, service exclusivity.

Only temporary test fixtures and inert state transitions. No live systemd,
Moltbook credentials, Gateway, production SQLite or external HTTP.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tests"))
from bob_v08.core import Action, Policy
from bob_v08.r3_cutover_rehearsal import (
    SourcePin, CutoverState, verified_source, rehearse_cutover,
    simulated_source_handoff, simulated_pause_state,
)
from bob_v08.r3_unified import UnifiedLab, Proof, _validated
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW


def make_saved_scout(root: Path, *, content="A source about safe ownership."):
    root.mkdir(mode=0o700)
    feed={"source":"Moltbook public API","fetched_at":"2026-10-30T23:00:00+00:00",
          "posts":[{"id":ID,"author":"SavedAgent","title":"Ownership and memory",
                    "content":content}]}
    raw=json.dumps(feed).encode("utf-8")
    sha=hashlib.sha256(raw).hexdigest()
    draft="Legacy Scout draft, distinct from Bob's new text."
    approval=hashlib.sha256((ID+"\n"+draft+"\n"+sha).encode()).hexdigest()
    result={"schema":2,"run_id":RUN,"status":"pending",
            "chosen_post_id":ID,"snapshot_file":"scout-feed-"+RUN+".json",
            "snapshot_sha256":sha,"approval_sha256":approval,
            "draft_comment":draft,
            "draft_sha256":hashlib.sha256(draft.encode()).hexdigest()}
    (root/("scout-feed-"+RUN+".json")).write_bytes(raw)
    (root/("scout-result-"+RUN+".json")).write_text(
        json.dumps(result),encoding="utf-8")
    return result


class SourceBoundary(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.source=self.root/"saved-scout"
        self.result=make_saved_scout(self.source)
        self.action=Action("comment",RUN,ID,"Technical source-based interest.",TEXT)
        self.db=self.root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.db)
        self.lab=UnifiedLab(self.db)
        self.marker=self.root/"paused"
        self.policy=consent_policy()
        self.proof=Proof(ID,NOW,"clear")

    def handoff(self, *, after_queue=None, policy=None, mode="auto", proof=None):
        return simulated_source_handoff(
            self.lab,self.source,self.action,at=NOW,mode=mode,
            policy=policy if policy is not None else self.policy,
            proof=proof if proof is not None else self.proof,
            pause_marker=self.marker,after_queue=after_queue)

    def test_genuine_verified_scout_bytes_are_reopened_for_each_boundary(self):
        observation,pin=verified_source(self.source,self.action)
        self.assertEqual((pin.source_run,pin.target_id),(RUN,ID))
        self.assertEqual(pin.snapshot_sha256,self.result["snapshot_sha256"])
        self.assertEqual(pin.scout_approval_sha256,self.result["approval_sha256"])
        self.assertEqual(verified_source(self.source,self.action,pinned=pin)[1],pin)
        # A distinct Bob-authored text obtains its own independent seal.
        seal,_=_validated(self.action,observation)
        self.assertNotEqual(seal,pin.scout_approval_sha256)
        outcome=self.handoff()
        self.assertEqual((outcome.state,outcome.reason),
                         ("intent_simulated","one_counted_synthetic_intent"))
        self.assertFalse(outcome.acted)
        self.assertTrue(outcome.simulated)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM publish_jobs "
                "WHERE state='sending_simulated' AND attempted_at IS NOT NULL"
                ).fetchone()[0],1)

    def test_tampered_unsealed_feed_is_held_without_attempt(self):
        def corrupt():
            (self.source/("scout-feed-"+RUN+".json")).write_text(
                '{"posts":[]}',encoding="utf-8")
        outcome=self.handoff(after_queue=corrupt)
        self.assertEqual((outcome.state,outcome.reason),
                         ("held","verified_source_drift"))
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT state,attempted_at FROM publish_jobs"
                ).fetchone(),("held_simulated",None))
        self.assertEqual(self.lab.simulated_hold_source(RUN,at=NOW).reason,
                         "not_queued_or_already_attempted")

    def test_fully_resealed_changed_scout_still_breaks_original_pin(self):
        _,pin=verified_source(self.source,self.action)
        make_saved_scout(self.source,content="An altered but internally sealed feed.")
        with self.assertRaisesRegex(ValueError,"source_changed_since_pin"):
            verified_source(self.source,self.action,pinned=pin)

    def test_scout_file_symlink_and_model_target_switch_fail_closed(self):
        snapshot=self.source/("scout-feed-"+RUN+".json")
        swapped=self.source/"raw.json"
        snapshot.rename(swapped)
        snapshot.symlink_to(swapped)
        with self.assertRaisesRegex(ValueError,"source_validation_failed"):
            verified_source(self.source,self.action)
        self.assertEqual(self.handoff().reason,"source_unverified")
        self.assertEqual(self.lab.path.stat().st_mode & 0o077,0)
        self.assertEqual(self._jobs(),0)

    def test_revoked_local_owner_dial_after_queue_blocks_intent(self):
        def revoke():
            with sqlite3.connect(self.db) as con:
                con.execute("UPDATE publish_settings SET value='off' "
                            "WHERE name='r3_comment_dial'")
        result=self.handoff(after_queue=revoke)
        self.assertEqual((result.state,result.reason),("held","owner_comment_dial_off"))
        self.assertEqual(self._attempts(),0)

    def test_global_pause_marker_appearing_after_queue_stops_intent(self):
        def pause():
            self.marker.touch()
            os.chmod(self.marker,0o600)
        result=self.handoff(after_queue=pause)
        self.assertEqual((result.state,result.reason),("held","paused_or_unknown"))
        self.assertEqual(self._attempts(),0)
        self.assertTrue(simulated_pause_state(self.marker))

    def test_symlink_pause_and_missing_pause_root_fail_closed(self):
        with tempfile.TemporaryDirectory() as another:
            (self.root/"paused").symlink_to(Path(another))
            self.assertTrue(simulated_pause_state(self.marker))
            self.assertEqual(self.handoff().reason,"paused_or_unknown")
        self.assertEqual(self._attempts(),0)
        self.assertTrue(simulated_pause_state(Path("/tmp")/"paused"))
        self.assertTrue(simulated_pause_state(self.root/"not-paused"))

    def test_missing_or_fabricated_preflight_cannot_create_eligible_intent(self):
        # A caller-supplied Proof is SYNTHETIC; this bridge never contacts Moltbook.
        result=self.handoff(proof=Proof(ID,NOW-timedelta(minutes=5),"clear"))
        self.assertEqual(result.reason,"preflight_stale_or_future")
        self.assertEqual(self._attempts(),0)

    def test_explicit_manual_approval_of_new_seal_not_legacy_scout(self):
        obs,_=verified_source(self.source,self.action)
        seal,_=_validated(self.action,obs)
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE publish_settings SET value='propose' "
                        "WHERE name='r3_comment_dial'")
            con.execute("INSERT INTO r3_owner_approvals VALUES(?,?,?,?)",
                        (RUN,seal,"approved",NOW.isoformat()))
        result=self.handoff(mode="manual",policy=consent_policy("propose"))
        self.assertEqual(result.state,"intent_simulated")
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT mode FROM publish_jobs").fetchone()[0],
                             "manual")

    def test_default_shadow_rejected_even_with_real_saved_scout(self):
        result=self.handoff(policy=Policy())
        self.assertEqual((result.state,result.reason),("refused","shadow_only"))
        self.assertEqual(self._attempts(),0)

    def _attempts(self):
        with sqlite3.connect(self.db) as con:
            return con.execute("SELECT COUNT(*) FROM publish_jobs "
                               "WHERE attempted_at IS NOT NULL").fetchone()[0]

    def _jobs(self):
        with sqlite3.connect(self.db) as con:
            return con.execute("SELECT COUNT(*) FROM publish_jobs").fetchone()[0]


class OwnershipRehearsal(unittest.TestCase):
    def test_explicit_gate_order_and_code_only_rollback_preserves_history(self):
        start=CutoverState(attempted=("old-attempt",),
                           uncertain=("old-uncertain",))
        self.assertFalse(rehearse_cutover(start,"activate",
                          owner_explicitly_authorized=True).accepted)
        staged=rehearse_cutover(start,"stage")
        self.assertTrue(staged.accepted)
        self.assertTrue(staged.state.legacy_publisher_timer)
        self.assertTrue(staged.state.shadow_timer)
        self.assertFalse(rehearse_cutover(staged.state,"quiesce",legacy_drained=True
                         ).accepted)
        quiesced=rehearse_cutover(
            staged.state,"quiesce",legacy_drained=True,
            backup_verified=True,rollback_rehearsed=True)
        self.assertTrue(quiesced.accepted)
        self.assertFalse(quiesced.state.legacy_publisher_timer)
        self.assertFalse(quiesced.state.candidate_publisher_timer)
        self.assertFalse(rehearse_cutover(quiesced.state,"activate",
            backup_verified=True,rollback_rehearsed=True,
            source_adapter_verified=True).accepted)
        candidate=rehearse_cutover(
            quiesced.state,"activate",owner_explicitly_authorized=True,
            source_adapter_verified=True,backup_verified=True,
            rollback_rehearsed=True)
        self.assertTrue(candidate.accepted)
        self.assertEqual(candidate.state.phase,"candidate")
        self.assertFalse(candidate.state.legacy_publisher_timer)
        self.assertTrue(candidate.state.candidate_publisher_timer)
        self.assertFalse(rehearse_cutover(candidate.state,"rollback").accepted)
        roll=rehearse_cutover(candidate.state,"rollback",candidate_drained=True)
        self.assertTrue(roll.accepted)
        self.assertEqual(roll.state.phase,"baseline")
        self.assertEqual(roll.state.attempted,("old-attempt",))
        self.assertEqual(roll.state.uncertain,("old-uncertain",))
        self.assertFalse(roll.changed_host)
        self.assertFalse(roll.published)

    def test_overlapping_or_legacy_system_writer_is_never_accepted(self):
        cases=(
            replace(CutoverState(),candidate_publisher_timer=True),
            replace(CutoverState(),candidate_publisher_running=True),
            replace(CutoverState(),legacy_system_scout_timer=True),
            replace(CutoverState(),legacy_publisher_timer=False),
        )
        for invalid in cases:
            with self.subTest(invalid=invalid):
                self.assertEqual(rehearse_cutover(invalid,"stage").reason,
                                 "invalid_or_overlapping_dispatchers")

    def test_active_workers_cannot_be_cut_over_or_rolled_back_without_drain(self):
        busy=CutoverState(legacy_publisher_running=True)
        stage=rehearse_cutover(busy,"stage")
        self.assertTrue(stage.accepted)
        self.assertEqual(rehearse_cutover(stage.state,"quiesce",
                         legacy_drained=True,backup_verified=True,
                         rollback_rehearsed=True).reason,"legacy_not_drained")
        self.assertEqual(rehearse_cutover(stage.state,"rollback"
                         ).reason,"legacy_not_drained")
        self.assertTrue(rehearse_cutover(stage.state,"rollback",
                        legacy_drained=True).accepted)

    def test_unknown_transition_and_forged_owner_metadata_do_not_enable(self):
        start=CutoverState()
        self.assertEqual(rehearse_cutover(start,"enable-new-publisher").reason,
                         "unknown_transition")
        staged=rehearse_cutover(start,"stage").state
        quiesced=rehearse_cutover(staged,"quiesce",
                                 legacy_drained=True,backup_verified=True,
                                 rollback_rehearsed=True).state
        refused=rehearse_cutover(quiesced,"activate",
                                owner_explicitly_authorized="YES",
                                source_adapter_verified=True,
                                backup_verified=True,rollback_rehearsed=True)
        self.assertFalse(refused.accepted)

    def test_static_inert_cli_reports_denied_cutover_and_history_preservation(self):
        sys.path.insert(0,str(ROOT/"scripts"))
        from rehearse_r3_cutover import report
        output=report()
        self.assertFalse(output["cutover_authorized"])
        self.assertEqual(output["owner_permission_absent"],"cutover_gate_not_met")
        self.assertTrue(output["attempt_history_preserved"])
        self.assertTrue(output["uncertain_history_preserved"])
        self.assertTrue(output["shadow_timer_unchanged"])
        self.assertEqual(output["network_attempts"],0)
        self.assertEqual(output["systemd_changes"],0)

    def test_no_actual_unit_actions_or_credentials_in_code(self):
        import bob_v08.r3_cutover_rehearsal as m
        source=inspect.getsource(m)
        for forbidden in ("subprocess", "urllib", "requests.", "api_key(",
                          "os.system(", "Popen(", "moltbook.com", "systemctl --user"):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
