"""R3 batched safety tests for the SAME legacy credentialed publisher.

All tests load the source publisher in a disposable in-memory SQLite database.
The network/credential functions are mocks. No installed runner or Moltbook POST.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.machinery
import importlib.util
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src" / "lib" / "bob")]

POST = "a9ccf436-c5d5-4849-af92-843670ab8271"
RECEIPT = "c9ccf436-c5d5-4849-af92-843670ab8271"
DIGEST = "a" * 64
CREATED = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SECONDARY = "20261030T010100Z"


def publisher():
    path = ROOT / "src" / "bin" / "bob-moltbook-publisher"
    loader = importlib.machinery.SourceFileLoader(
        "bob_r3_original_publisher_guard_fixture", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class LegacySingleWriterSafetyTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute(
            "CREATE TABLE publish_jobs("
            "run_id TEXT PRIMARY KEY, approval_sha256 TEXT,"
            "post_id TEXT, draft_comment TEXT, mode TEXT, state TEXT,"
            "created_at TEXT, attempted_at TEXT, updated_at TEXT,"
            "comment_id TEXT, last_error TEXT)")
        self.db.execute(
            "CREATE TABLE decisions(run_id TEXT PRIMARY KEY,"
            "draft_sha256 TEXT,status TEXT)")
        self.db.execute(
            "INSERT INTO publish_jobs "
            "(run_id,approval_sha256,post_id,draft_comment,mode,state,created_at,updated_at)"
            "VALUES(?,?,?,?,?,?,?,?)",
            (CREATED, DIGEST, POST, "Saved original Scout draft", "manual",
             "queued", CREATED, CREATED))
        self.db.execute(
            "INSERT INTO decisions VALUES(?,?,'approved')", (CREATED,DIGEST))
        self.db.execute(
            "INSERT INTO publish_jobs "
            "(run_id,approval_sha256,post_id,draft_comment,mode,state,created_at,updated_at)"
            "VALUES(?,?,?,?,?,?,?,?)",
            (SECONDARY, "b"*64, POST, "Different old draft", "auto",
             "failed", SECONDARY, SECONDARY))
        self.db.commit()
        self.p = publisher()
        self.p.auto_candidates = lambda db: 0
        self.p.checkpoint = lambda *args, **kwargs: None
        self.p.event = lambda *args, **kwargs: None
        self.p.record_publisher_skip = lambda *args, **kwargs: None
        self.p.can_send = lambda *args, **kwargs: (True, "fixture")
        self.p.load_record = lambda rid: {
            "approval_sha256": DIGEST,
            "chosen_post_id": POST,
            "draft_comment": "Saved original Scout draft"}
        self.calls = []

    def state(self):
        return self.db.execute(
            "SELECT state, attempted_at FROM publish_jobs WHERE run_id=?",
            (CREATED,)).fetchone()

    def test_failed_after_attempt_blocks_same_target_before_preflight(self):
        self.db.execute(
            "UPDATE publish_jobs SET attempted_at=? WHERE run_id=?",
            ("2026-10-30T01:01:00+00:00", SECONDARY))
        self.db.commit()
        self.p.api = lambda *args, **kwargs: self.fail(
            "duplicate target must never call public GET or POST")
        self.p.api_key = lambda: self.fail("credentials must remain untouched")
        result = self.p.publisher_step(self.db)
        self.assertEqual(result, "duplicate target blocked")
        self.assertEqual(self.state()[0], "failed")
        self.assertIsNone(self.state()[1])

    def test_new_attempt_during_public_get_blocks_atomic_final_claim(self):
        def api(method, path, payload=None, *, key=None):
            self.calls.append(method)
            if method != "GET":
                self.fail("late attempted duplicate must block POST")
            self.db.execute(
                "UPDATE publish_jobs SET attempted_at=? WHERE run_id=?",
                ("2026-10-31T01:01:00+00:00", SECONDARY))
            self.db.commit()
            return {"data": {"post": {"id": POST}}}
        self.p.api = api
        self.p.api_key = lambda: self.fail("no credentials before claim")
        outcome = self.p.publisher_step(self.db)
        self.assertIn("changed; not sent", outcome)
        self.assertEqual(self.calls, ["GET"])
        self.assertEqual(self.state(), ("queued", None))

    def test_original_unattempted_failed_job_does_not_block_intent(self):
        def api(method, path, payload=None, *, key=None):
            self.calls.append(method)
            if method == "GET":
                return {"data": {"post": {"id": POST}}}
            self.assertEqual((method, path),
                             ("POST", "/posts/"+POST+"/comments"))
            self.assertEqual(payload, {"content":"Saved original Scout draft"})
            self.assertEqual(key, "synthetic-only-key")
            return {"success": True, "comment":{"id":RECEIPT}}
        self.p.api=api
        self.p.api_key=lambda:"synthetic-only-key"
        result=self.p.publisher_step(self.db)
        self.assertIn("comment published",result)
        self.assertEqual(self.calls,["GET","POST"])
        self.assertEqual(self.state()[0],"published")
        self.assertIsNotNone(self.state()[1])

    def test_r3_wide_dispatch_flags_still_off_and_canary_not_armed(self):
        # The single publisher can import the scoped canary adapter, but
        # without a private owner-arm it must follow original legacy behavior.
        self.assertFalse(self.p.R313C_INTEGRATION_COMPILED_OFF)
        import bob_r312_adapter, bob_r313c_adapter, bob_r3_canary_lock
        self.assertFalse(bob_r312_adapter.R312_REAL_DISPATCH)
        self.assertFalse(bob_r313c_adapter.R313C_REAL_DISPATCH)
        self.assertTrue(bob_r313c_adapter.R3_EXACT_CANARY_COMPILED)
        self.assertFalse(bob_r313c_adapter.production_dispatch_enabled())


if __name__ == "__main__":
    unittest.main()
