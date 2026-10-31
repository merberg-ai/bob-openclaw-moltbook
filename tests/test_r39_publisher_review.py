"""R3.9 tests: verified R3 origin and immutable read-only review, no live POST."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import inspect
import json
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
from bob_v08.core import Action
from bob_v08.r39_publisher_review import (
    AdmissionReview, RemoteReview, HOST, GET_TIMEOUT_SECONDS,
    MAX_REMOTE_BYTES, public_get_post, review_publisher_admission,
)
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_v08.r3_unified import UnifiedLab
from bob_v08.r3_unified import _validated
from test_r3_cutover_rehearsal import make_saved_scout
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW


class FakeGetResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self.payload = payload
    def read(self, max_bytes):
        return self.payload[:max_bytes]


class FixedHostGetTests(unittest.TestCase):
    def factory(self, payload, *, status=200):
        seen = []
        holder = {}
        class FakeHTTPS:
            def __init__(self, host, timeout):
                self.closed = False
                seen.append((host, timeout))
                holder["connection"] = self
            def request(self, method, path, headers):
                seen.append((method, path, headers))
            def getresponse(self):
                return FakeGetResponse(payload, status)
            def close(self):
                self.closed = True
        return FakeHTTPS, seen, holder

    def test_exact_fixed_hostname_path_and_no_credentials_sent(self):
        body = json.dumps({"data": {"post": {
            "id": ID, "author": {"name": "SavedAgent"}}}}).encode()
        factory, seen, holder = self.factory(body)
        result = public_get_post(ID, "savedagent", connection_factory=factory)
        self.assertEqual(result, RemoteReview(True, "target_and_author_match"))
        self.assertEqual(seen[0], (HOST, GET_TIMEOUT_SECONDS))
        method, path, headers = seen[1]
        self.assertEqual((method, path), ("GET", "/api/v1/posts/" + ID))
        self.assertEqual(headers["Accept"], "application/json")
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("Cookie", headers)
        self.assertTrue(holder["connection"].closed)

    def test_rejects_untrusted_target_before_connection_instantiation(self):
        def never(*args, **kwargs):
            raise AssertionError("no connect")
        for target in ("https://evil.invalid/posts/foo", "/posts/1", ID + "?foo=1",
                       "invalid-id", "", None):
            self.assertEqual(public_get_post(target, "SavedAgent",
                 connection_factory=never).reason, "invalid_preflight_identity")

    def test_redirect_errors_and_non200_never_follow_another_host(self):
        good = json.dumps({"data": {"post": {
            "id": ID, "author": "SavedAgent"}}}).encode()
        for status in (301, 302, 307, 401, 404, 500):
            with self.subTest(status=status):
                factory, seen, holder = self.factory(good, status=status)
                result = public_get_post(ID, "SavedAgent", connection_factory=factory)
                self.assertFalse(result.matched)
                self.assertEqual(result.reason, "public_get_unavailable")
                self.assertEqual(len([x for x in seen if x[0] == "GET"]), 1)
                self.assertTrue(holder["connection"].closed)

    def test_deleted_wrong_id_wrong_author_and_missing_identity_refused(self):
        cases = [
            ({}, "target_identity_mismatch"),
            ({"id": ID, "author": "OtherAgent"}, "author_identity_mismatch"),
            ({"id": ID, "author": None}, "author_identity_mismatch"),
            ({"id": ID, "author": "SavedAgent", "deleted": True}, "target_deleted"),
            ({"id": ID, "author": "SavedAgent", "is_deleted": True}, "target_deleted"),
            ({"id": "33333333-3333-4333-8333-333333333333",
              "author": "SavedAgent"}, "target_identity_mismatch"),
        ]
        for payload, reason in cases:
            with self.subTest(reason=reason):
                factory, *_ = self.factory(json.dumps({"post": payload}).encode())
                result = public_get_post(ID, "SavedAgent", connection_factory=factory)
                self.assertEqual(result.reason, reason)
                self.assertFalse(result.matched)

    def test_malformed_oversize_failed_response_and_connection_error_refused(self):
        for body in (b"{", b"", b"[" + b"x"*MAX_REMOTE_BYTES,
                     json.dumps({"success": False,
                        "post": {"id": ID, "author": "SavedAgent"}}).encode()):
            factory, *_ = self.factory(body)
            result = public_get_post(ID, "SavedAgent", connection_factory=factory)
            self.assertFalse(result.matched)
        def broken(*args, **kwargs):
            raise OSError("no host")
        self.assertEqual(public_get_post(ID, "SavedAgent",
            connection_factory=broken).reason, "public_get_error")


class AdmissionContractTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "scout"
        make_saved_scout(self.source)
        self.action = Action("comment", RUN, ID, "Technical systems discussion.", TEXT)
        self.obs, self.pin = verified_source(self.source, self.action)
        self.dbpath = self.root / "r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.dbpath)
        self.lab = UnifiedLab(self.dbpath)
        with sqlite3.connect(self.dbpath) as db:
            db.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
        self.assertEqual(self.lab.propose(self.action, self.obs, at=NOW).state,
                         "proposed")
        self.assertEqual(self.lab.queue(self.action, self.obs, mode="auto",
                         at=NOW, policy=consent_policy()).state,
                         "queued_simulated")
        self.pause_marker = self.root / "paused"

    def run_review(self, *, public_get=None, clock=None, mode="auto"):
        with sqlite3.connect(self.dbpath) as db:
            return review_publisher_admission(
                db, self.source, self.action, mode=mode,
                pause_marker=self.pause_marker,
                clock=clock or (lambda: NOW),
                public_get=public_get or (
                    lambda _pid, _author: RemoteReview(True,"target_and_author_match")))

    def attempts(self):
        with sqlite3.connect(self.dbpath) as db:
            return db.execute("SELECT state,attempted_at FROM publish_jobs").fetchone()

    def test_verified_new_bob_draft_review_never_dispatches(self):
        before = self.dbpath.read_bytes()
        result = self.run_review()
        self.assertEqual((result.status, result.reason),
                         ("reviewed", "needs_single_publisher_atomic_intent_and_final_pause"))
        self.assertTrue(result.source_verified)
        self.assertTrue(result.owner_consent_observed)
        self.assertTrue(result.remote_target_verified)
        self.assertFalse(result.dispatch_authorized)
        self.assertFalse(result.acted)
        self.assertEqual(self.attempts(), ("queued", None))
        self.assertEqual(self.dbpath.read_bytes(), before)

    def test_real_existing_legacy_auto_enabled_does_not_grant_r3_permission(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute("UPDATE publish_settings SET value='0' "
                       "WHERE name='r3_auto_enabled'")
        result = self.run_review()
        self.assertEqual(result.reason, "separate_r3_auto_consent_required")
        self.assertIsNone(self.attempts()[1])

    def test_missing_or_off_owner_dial_blocks_without_post_get(self):
        calls=[]
        with sqlite3.connect(self.dbpath) as db:
            db.execute("DELETE FROM publish_settings WHERE name='r3_comment_dial'")
        result=self.run_review(public_get=lambda *_: calls.append(True))
        self.assertEqual(result.reason,"owner_r3_dial_off")
        self.assertEqual(calls,[])
        self.assertEqual(self.attempts(),("queued",None))

    def test_stale_or_wrong_external_result_is_not_permission(self):
        for response in (
            RemoteReview(False,"target_identity_mismatch"),
            RemoteReview(False,"author_identity_mismatch"),
            {"matched": True},
            None,
        ):
            with self.subTest(response=response):
                result=self.run_review(public_get=lambda *_: response)
                self.assertEqual(result.status,"refused")
                self.assertFalse(result.dispatch_authorized)
                self.assertIsNone(self.attempts()[1])

    def test_pause_and_owner_revocation_during_get_fail_second_read(self):
        def pause(*_):
            self.pause_marker.touch(mode=0o600)
            return RemoteReview(True,"target_and_author_match")
        self.assertEqual(self.run_review(public_get=pause).reason,
                         "recheck_paused_or_untrusted_marker")
        self.pause_marker.unlink()
        def revoke(*_):
            with sqlite3.connect(self.dbpath) as db:
                db.execute("UPDATE publish_settings SET value='off' "
                           "WHERE name='r3_comment_dial'")
            return RemoteReview(True,"target_and_author_match")
        self.assertEqual(self.run_review(public_get=revoke).reason,
                         "recheck_owner_r3_dial_off")
        self.assertEqual(self.attempts(),("queued",None))

    def test_friend_saved_while_get_running_blocks(self):
        def become_friend(*_):
            with sqlite3.connect(self.dbpath) as db:
                db.execute("INSERT INTO bob_friends VALUES('savedagent')")
            return RemoteReview(True,"target_and_author_match")
        self.assertEqual(self.run_review(public_get=become_friend).reason,
                         "recheck_friend_friend_target_protected")
        self.assertIsNone(self.attempts()[1])

    def test_source_changes_during_get_blocks(self):
        def corrupt(*_):
            file=self.source/("scout-feed-"+RUN+".json")
            file.write_text('{"posts":[]}',encoding="utf-8")
            return RemoteReview(True,"target_and_author_match")
        result=self.run_review(public_get=corrupt)
        self.assertEqual(result.reason,"recheck_not_a_new_sealed_bob_draft")
        self.assertIsNone(self.attempts()[1])

    def test_auto_budget_decreased_during_get_blocks(self):
        def lower(*_):
            with sqlite3.connect(self.dbpath) as db:
                db.execute("UPDATE publish_settings SET value='0' "
                           "WHERE name='activity_limit_comment_auto_daily'")
            return RemoteReview(True,"target_and_author_match")
        self.assertEqual(self.run_review(public_get=lower).reason,
                         "recheck_legacy_rate_or_budget")
        self.assertIsNone(self.attempts()[1])

    def test_old_legacy_queue_gets_manual_priority(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute(
                "INSERT INTO publish_jobs (run_id,approval_sha256,post_id,"
                "draft_comment,mode,state,created_at,updated_at)"
                " VALUES(?,?,?,?,?,'queued',?,?)",
                ("20261030T200000Z", "a"*64,
                 "33333333-3333-4333-8333-333333333333",
                 "Original manually approved Scout text","manual",NOW.isoformat(),
                 NOW.isoformat()))
        self.assertEqual(self.run_review().reason,"manual_first_queue_priority")
        self.assertIsNone(self.attempts()[1])

    def test_uncertain_attempt_on_same_target_prevents_review(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute(
                "INSERT INTO publish_jobs (run_id,approval_sha256,post_id,"
                "draft_comment,mode,state,created_at,attempted_at,updated_at)"
                " VALUES(?,?,?,?,?,'failed',?,?,?)",
                ("20261030T200000Z","a"*64,ID,
                 "Old failed but attempted comment","manual",
                 NOW.isoformat(),NOW.isoformat(),NOW.isoformat()))
        result=self.run_review()
        self.assertEqual(result.reason,"duplicate_or_uncertain_target")
        self.assertFalse(result.dispatch_authorized)

    def test_manual_admission_requires_exact_bob_seal_owner_approval(self):
        with sqlite3.connect(self.dbpath) as db:
            db.execute("UPDATE publish_jobs SET mode='manual'")
            db.execute("UPDATE publish_settings SET value='propose' "
                       "WHERE name='r3_comment_dial'")
        self.assertEqual(self.run_review(mode="manual").reason,
                         "new_bob_draft_approval_missing")
        seal,_=_validated(self.action,self.obs)
        with sqlite3.connect(self.dbpath) as db:
            db.execute("INSERT INTO r3_owner_approvals VALUES(?,?,?,?)",
                       (RUN,seal,"approved",NOW.isoformat()))
        good=self.run_review(mode="manual")
        self.assertEqual(good.status,"reviewed")
        self.assertFalse(good.dispatch_authorized)

    def test_stale_clock_or_external_failure_never_advances_job(self):
        clock=iter([NOW,NOW+timedelta(minutes=3)])
        self.assertEqual(self.run_review(clock=lambda:next(clock)).reason,
                         "preflight_clock_stale")
        def down(*_):
            raise TimeoutError("network not available")
        self.assertEqual(self.run_review(public_get=down).reason,"public_get_error")
        self.assertEqual(self.attempts(),("queued",None))

    def test_review_code_cannot_post_claim_or_write_real_queue(self):
        import bob_v08.r39_publisher_review as module
        source=inspect.getsource(module)
        for forbidden in (
            "subprocess.run(", "os.system(", "INSERT INTO publish_jobs",
            "UPDATE publish_jobs", "api_key(", "Authorization", "POST",
            "moltbook_"):
            self.assertNotIn(forbidden,source)
        result=self.run_review()
        self.assertIsInstance(result,AdmissionReview)
        self.assertFalse(result.dispatch_authorized)


if __name__ == "__main__":
    unittest.main()
