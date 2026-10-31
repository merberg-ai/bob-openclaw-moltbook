"""R3.7 publisher-side authorization rehearsal: offline, isolated, zero POSTs."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import inspect
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from bob_v08.core import Action
from bob_v08.r37_trusted_gate_lab import rehearse_trusted_gate
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_v08.r3_unified import UnifiedLab, _validated
from test_r3_cutover_rehearsal import make_saved_scout
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW


class TrustedGateRehearsal(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "scout"
        self.record = make_saved_scout(self.source)
        self.action = Action("comment", RUN, ID, "Careful technical interest.", TEXT)
        self.obs, _ = verified_source(self.source, self.action)
        self.db = self.root / "r3-unified-fixtures" / "r3-unified-lab.sqlite3"
        fixture(self.db)
        self.lab = UnifiedLab(self.db)
        self.pause_marker = self.root / "paused"
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
        self.assertEqual(self.lab.propose(self.action, self.obs, at=NOW).state, "proposed")
        self.assertEqual(
            self.lab.queue(self.action, self.obs, mode="auto", at=NOW,
                           policy=consent_policy()).state, "queued_simulated")

    def run_gate(self, *, get_post=None, clock=None, mode="auto"):
        if get_post is None:
            get_post = lambda pid: {"data": {"post": {
                "id": pid, "author": "SavedAgent", "deleted": False}}}
        if clock is None:
            clock = lambda: NOW
        return rehearse_trusted_gate(
            self.lab, self.source, self.action, mode=mode,
            pause_marker=self.pause_marker, get_post=get_post, clock=clock)

    def state(self):
        with sqlite3.connect(self.db) as conn:
            return conn.execute(
                "SELECT state,attempted_at FROM publish_jobs WHERE run_id=?",
                (RUN,)).fetchone()

    def test_correct_get_and_trusted_host_gates_record_one_synthetic_intent(self):
        result = self.run_gate()
        self.assertEqual((result.state, result.reason),
                         ("intent_simulated", "one_counted_synthetic_intent"))
        self.assertFalse(result.dispatch_authorized)
        self.assertFalse(result.acted)
        self.assertTrue(result.simulated)
        self.assertIsNotNone(self.state()[1])
        self.assertEqual(self.run_gate().reason, "not_a_new_sealed_bob_draft")
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM r3_lab_audit "
                "WHERE reason='sending_simulated'").fetchone()[0], 1)

    def test_get_must_match_exact_id_and_author_not_merely_http_success(self):
        for response in (
            {}, {"success": True}, {"data": {"post": {"author": "SavedAgent"}}},
            {"data": {"post": {"id": ID}}},
            {"data": {"post": {"id": "33333333-3333-4333-8333-333333333333",
                                "author": "SavedAgent"}}},
            {"data": {"post": {"id": ID, "author": "OtherAgent"}}},
            {"data": {"post": {"id": ID, "author": "SavedAgent", "deleted": True}}},
            {"success": False, "data": {"post": {"id": ID, "author": "SavedAgent"}}},
        ):
            with self.subTest(response=response):
                result = self.run_gate(get_post=lambda _pid: response)
                self.assertEqual(result.reason, "get_target_author_unverified")
                self.assertIsNone(self.state()[1])

    def test_preflight_timeout_and_bad_clock_block_without_attempt(self):
        def timeout(_pid):
            raise TimeoutError("simulated timeout")
        self.assertEqual(self.run_gate(get_post=timeout).reason,
                         "get_or_source_unverified")
        calls = iter([NOW, NOW + timedelta(minutes=3)])
        self.assertEqual(self.run_gate(clock=lambda: next(calls)).reason,
                         "get_stale_or_clock_changed")
        calls = iter([NOW, NOW - timedelta(seconds=1)])
        self.assertEqual(self.run_gate(clock=lambda: next(calls)).reason,
                         "get_stale_or_clock_changed")
        self.assertIsNone(self.state()[1])

    def test_existing_legacy_auto_setting_cannot_consent_to_bob_auto(self):
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE publish_settings SET value='0' "
                       "WHERE name='r3_auto_enabled'")
        result = self.run_gate()
        self.assertEqual(result.reason, "separate_auto_consent_missing")
        self.assertIsNone(self.state()[1])

    def test_owner_dial_revoked_during_get_is_rechecked(self):
        def revoke(pid):
            with sqlite3.connect(self.db) as con:
                con.execute("UPDATE publish_settings SET value='off' "
                            "WHERE name='r3_comment_dial'")
            return {"data": {"post": {"id": pid, "author": "SavedAgent"}}}
        result = self.run_gate(get_post=revoke)
        self.assertEqual(result.reason, "recheck_owner_dial_off")
        self.assertIsNone(self.state()[1])

    def test_auto_flag_revoked_during_get_is_rechecked(self):
        def revoke(pid):
            with sqlite3.connect(self.db) as con:
                con.execute("UPDATE publish_settings SET value='0' "
                            "WHERE name='auto_enabled'")
            return {"data": {"post": {"id": pid, "author": "SavedAgent"}}}
        result = self.run_gate(get_post=revoke)
        self.assertEqual(result.reason, "recheck_separate_auto_consent_missing")
        self.assertIsNone(self.state()[1])

    def test_pause_marker_appearing_during_get_denies(self):
        def pause(pid):
            self.pause_marker.touch()
            return {"data": {"post": {"id": pid, "author": "SavedAgent"}}}
        result = self.run_gate(get_post=pause)
        self.assertEqual(result.reason, "recheck_paused_or_untrusted_marker")
        self.assertIsNone(self.state()[1])

    def test_forged_friend_batch_tag_denied_even_if_author_not_saved_friend(self):
        file = self.source / ("scout-feed-" + RUN + ".json")
        # This test demonstrates that changing feed bytes without updating the
        # already sealed Scout report is rejected before the friend decision.
        feed = json.loads(file.read_text())
        feed["posts"][0]["from_friend"] = True
        file.write_text(json.dumps(feed), encoding="utf-8")
        result = self.run_gate()
        self.assertEqual(result.reason, "saved_source_unverified")
        self.assertIsNone(self.state()[1])

    def test_saved_friend_in_private_table_denies(self):
        with sqlite3.connect(self.db) as con:
            con.execute("INSERT INTO bob_friends VALUES('savedagent')")
        result = self.run_gate()
        self.assertEqual(result.reason, "friend_target_protected")
        self.assertIsNone(self.state()[1])

    def test_absent_or_damaged_friend_table_never_becomes_clear(self):
        with sqlite3.connect(self.db) as con:
            con.execute("DROP TABLE bob_friends")
        self.assertEqual(self.run_gate().reason, "friend_table_missing")
        with sqlite3.connect(self.db) as con:
            con.execute("CREATE TABLE bob_friends(bogus TEXT)")
        self.assertEqual(self.run_gate().reason, "friend_guard_unavailable")
        self.assertIsNone(self.state()[1])

    def test_friend_added_while_get_in_flight_is_rechecked(self):
        def new_friend(pid):
            with sqlite3.connect(self.db) as con:
                con.execute("INSERT INTO bob_friends VALUES('savedagent')")
            return {"data": {"post": {"id": pid, "author": "SavedAgent"}}}
        self.assertEqual(self.run_gate(get_post=new_friend).reason,
                         "recheck_friend_target_protected")
        self.assertIsNone(self.state()[1])

    def test_manual_first_legacy_job_prevents_bob_auto(self):
        with sqlite3.connect(self.db) as db:
            db.execute(
                "INSERT INTO publish_jobs(run_id,approval_sha256,post_id,"
                "draft_comment,mode,state,created_at,updated_at) "
                "VALUES(?,?,?,?,?,'queued',?,?)",
                ("20261030T200000Z", "a"*64,
                 "33333333-3333-4333-8333-333333333333",
                 "Another manual approved draft", "manual", NOW.isoformat(),
                 NOW.isoformat()))
        result = self.run_gate()
        self.assertEqual(result.reason, "manual_first_queue_priority")
        self.assertIsNone(self.state()[1])

    def test_legacy_uncertain_attempt_to_same_target_blocks_auto(self):
        with sqlite3.connect(self.db) as db:
            db.execute(
                "INSERT INTO publish_jobs(run_id,approval_sha256,post_id,"
                "draft_comment,mode,state,created_at,attempted_at,updated_at) "
                "VALUES(?,?,?,?,?,'uncertain',?,?,?)",
                ("20261030T200000Z", "a"*64, ID, "Earlier uncertain",
                 "manual", NOW.isoformat(), NOW.isoformat(), NOW.isoformat()))
        result = self.run_gate()
        self.assertEqual(result.reason, "duplicate_or_uncertain_target")
        self.assertIsNone(self.state()[1])

    def test_policy_limit_lowered_during_get_blocks_with_no_attempt(self):
        def lower(pid):
            with sqlite3.connect(self.db) as db:
                db.execute("UPDATE publish_settings SET value='0' "
                           "WHERE name='activity_limit_comment_auto_daily'")
            return {"data": {"post": {"id": pid, "author": "SavedAgent"}}}
        result = self.run_gate(get_post=lower)
        self.assertEqual(result.reason, "recheck_legacy_budget_or_spacing")
        self.assertIsNone(self.state()[1])

    def test_manual_mode_requires_exact_separately_approved_bob_seal(self):
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE publish_jobs SET mode='manual' WHERE run_id=?", (RUN,))
        self.assertEqual(self.run_gate(mode="manual").reason,
                         "specific_bob_draft_not_approved")
        seal, _ = _validated(self.action, self.obs)
        with sqlite3.connect(self.db) as db:
            db.execute(
                "INSERT INTO r3_owner_approvals VALUES(?,?,?,?)",
                (RUN, seal, "approved", NOW.isoformat()))
        accepted = self.run_gate(mode="manual")
        self.assertEqual(accepted.state, "intent_simulated")
        self.assertFalse(accepted.dispatch_authorized)

    def test_r37_module_cannot_load_credentials_or_dispatch_itself(self):
        import bob_v08.r37_trusted_gate_lab as target
        source = inspect.getsource(target)
        for forbidden in ("urllib.request", "requests.", "api_key(",
                          "subprocess.run(", "OPENER.open(",
                          "CREDS.read_text", "moltbook.com"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
