"""Bounded R4 read-only projection and mobile/authenticated UI tests."""
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_projection as projection
import bob_r4_web as web

RUN="20261101T151033Z"
ATTEMPT="2026-11-01T19:46:08+00:00"


class R4ProjectionTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="r4-private-snapshot-")
        self.addCleanup(t.cleanup)
        self.path=Path(t.name)/"activity-queue.sqlite3"
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT);
                CREATE TABLE publish_jobs(
                    run_id TEXT,state TEXT,mode TEXT,attempted_at TEXT,
                    comment_id TEXT,created_at TEXT);
                CREATE TABLE r3_proposals(source_run TEXT,state TEXT);
                CREATE TABLE bob_memories(
                    title TEXT,category TEXT,confidence TEXT,state TEXT,
                    source_kind TEXT,updated_at TEXT);
                CREATE TABLE bob_friends(
                    handle TEXT,relationship TEXT,source_kind TEXT,
                    state TEXT,updated_at TEXT);
                CREATE TABLE original_posts(id TEXT);
                CREATE TABLE r3_lab_audit(
                    id INTEGER PRIMARY KEY,source_run TEXT,event TEXT,at TEXT);
            """)
            db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?,?,?)",
                (RUN,"published","manual",ATTEMPT,
                 "8c37f88f-e678-4007-ba56-586b76ef4cfd",ATTEMPT))
            db.execute("INSERT INTO r3_proposals VALUES(?,?)",
                       (RUN,"published"))
            db.execute("INSERT INTO bob_memories VALUES(?,?,?,?,?,?)",
                ("Observe unusual systems","observation","medium",
                 "active","operator",ATTEMPT))
            db.execute("INSERT INTO bob_friends VALUES(?,?,?,?,?)",
                ("Friend_One","interesting","manual","active",ATTEMPT))
            db.execute("INSERT INTO r3_lab_audit VALUES(1,?,?,?)",
                       (RUN,"r313c_receipt",ATTEMPT))

    def test_read_only_source_and_attempt_distinctions(self):
        s=projection.snapshot(self.path)
        self.assertTrue(s["available"])
        self.assertTrue(s["read_only"])
        self.assertEqual(s["attempted"],1)
        self.assertEqual(s["recent_jobs"][0]["state"],"published")
        self.assertTrue(s["recent_jobs"][0]["attempt_recorded"])
        self.assertTrue(s["recent_jobs"][0]["api_acknowledged"])
        self.assertEqual(s["recent_jobs"][0]["publicly_visible"],"not_checked")
        self.assertFalse(s["publicly_verified_by_current_view"])
        self.assertEqual(s["people"][0]["remote_following"],"unknown")
        self.assertEqual(s["people"][0]["local_relationship"],"interesting")
        self.assertEqual(s["memory_titles"][0]["provenance"],
                         "operator_entered_not_agent_recall")
        self.assertEqual(s["controls"]["follow"],"off")
        self.assertTrue(s["r4_paused"])
        self.assertEqual(s["external_write_requests"],0)
        self.assertEqual(s["latest_r3_source"],RUN)

    def test_missing_corrupted_and_unrecognized_schema_fail_closed(self):
        self.assertFalse(projection.snapshot(self.path.parent/"missing.db")["available"])
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO publish_settings VALUES('r4_mode_follow','yes')")
        result=projection.snapshot(self.path)
        self.assertFalse(result["available"])
        self.assertTrue(result["r4_paused"])
        self.assertEqual(result["controls"]["follow"],"off")

    def test_bounded_read_does_not_rewrite_original_comment(self):
        first=self.path.read_bytes()
        result=projection.snapshot(self.path)
        self.assertTrue(result["available"])
        self.assertEqual(self.path.read_bytes(),first)
        self.assertFalse((self.path.parent/"missing.db").exists())


class R4PageTests(unittest.TestCase):
    def data(self):
        s=projection.empty()
        s["available"]=True
        s["people"]=[dict(handle="<script>alert(1)</script>",
                          local_relationship="friend",
                          evidence="owner_entry",remote_following="unknown")]
        s["memory_titles"]=[dict(title="<img src=x onerror=evil()>",
                                 category="observation",confidence="low")]
        return s

    def test_six_routes_render_and_escape_owner_text(self):
        d=self.data()
        for panel in ("now","inbox","bob","controls","diagnostics","chat"):
            with self.subTest(panel=panel):
                html=web.content(panel,d,"csrf-test")
                self.assertIn("380px",html)
                self.assertIn('aria-label="Bob R4 sections"',html)
                self.assertNotIn("<script>alert(1)</script>",html)
                self.assertNotIn("<img src=x onerror=evil()>",html)
                self.assertIn("/r4/controls",html)
        bob=web.content("bob",d,"csrf-test")
        self.assertIn("&lt;img",bob)
        self.assertIn("remote following unknown",bob)
        controls=web.content("controls",d,"csrf-test")
        self.assertIn('value="auto" disabled',controls)
        self.assertIn("SET R4 FOLLOW PROPOSE",controls)
        self.assertIn('name="csrf"',controls)
        self.assertIn('href="/r4/chat"',controls)

    def test_r4_does_not_rename_or_capture_legacy_routes(self):
        self.assertEqual(web.PANEL["/r4/now"],"now")
        self.assertNotIn("/r3",web.PAGES)
        self.assertNotIn("/moltbook/friends",web.PAGES)
        self.assertNotIn("/api/system/status",web.PAGES)
        self.assertNotIn("/console",web.PAGES)

    def test_handler_auth_host_and_legacy_delegate(self):
        class Legacy:
            def __init__(self):
                self.path="/r4/now";self.response=None;self.good_host=True
                self.good_auth=True
            def _valid_host(self): return self.good_host
            def _authenticated(self): return self.good_auth
            def _auth_required(self): self.response="auth_required"
            def _send(self,status,*args): self.response=status
            def do_GET(self): self.response="legacy"
        class Handler(web.R4HandlerMixin,Legacy):
            R4_CSRF_TOKEN="synthetic"
        h=Handler()
        h.good_host=False
        h.do_GET()
        self.assertEqual(h.response,403)
        h.good_host=True;h.good_auth=False
        h.do_GET()
        self.assertEqual(h.response,"auth_required")
        h.path="/r3";h.good_auth=True
        h.do_GET()
        self.assertEqual(h.response,"legacy")
        h.path="/r4/bob"
        fake=types.ModuleType("navigation_shell")
        fake.wrap=lambda title,content,path: content
        with patch.dict(sys.modules,{"navigation_shell":fake}), \\
                patch.object(web,"snapshot",return_value=self.data()):
            h.do_GET()
        self.assertEqual(h.response,200)


if __name__=="__main__":
    unittest.main()
