"""Focused offline acceptance for Bob Overview.

Synthetic SQLite only. No network, credentials, live database, or publisher.
"""
from __future__ import annotations

import ast
from datetime import datetime,timezone
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src/lib/bob"))
sys.path.insert(0,str(ROOT/"webui"))
import bob_overview as overview
import build_v072_overview_candidate as candidate
import build_v072_activity_limits_candidate as previous


def sample_db(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execute("INSERT INTO publish_settings VALUES('auto_enabled','1')")
        for name,value in (("comment_daily","8"),("comment_gap_minutes","30"),
                           ("comment_auto_daily","4"),("original_daily","4"),
                           ("original_gap_minutes","120")):
            db.execute("INSERT INTO publish_settings VALUES(?,?)",
                       ("activity_limit_"+name,value))
        db.execute("CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,mode TEXT,state TEXT,"
                   "attempted_at TEXT)")
        db.execute("CREATE TABLE original_posts(id TEXT PRIMARY KEY,state TEXT,attempted_at TEXT,visible INTEGER)")
        db.execute("CREATE TABLE original_requests(id TEXT PRIMARY KEY,state TEXT)")
        db.execute("CREATE TABLE published_replies(id TEXT PRIMARY KEY)")
        db.execute("CREATE TABLE original_post_replies(id TEXT PRIMARY KEY)")
        db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,kind TEXT)")
        for id,mode,state,time in (
            ("a","manual","published","2026-10-29T09:00:00+00:00"),
            ("b","manual","queued",None),
            ("c","auto","queued",None),
            ("d","manual","uncertain","2026-10-29T10:00:00+00:00"),
            ("e","auto","published","2026-10-29T12:00:00+00:00"),
        ):
            db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",(id,mode,state,time))
        for row in (("x","draft",None,0),("y","approved",None,0),
                    ("z","published","2026-10-29T08:00:00+00:00",1)):
            db.execute("INSERT INTO original_posts VALUES(?,?,?,?)",row)
        db.execute("INSERT INTO original_requests VALUES('gen','running')")
        db.execute("INSERT INTO published_replies VALUES('reply')")
        db.execute("INSERT INTO original_post_replies VALUES('original-reply')")
        db.execute("INSERT INTO publish_events(at,kind) VALUES(?,?)",
                   ("2026-10-29T12:00:00+00:00","<script>untrusted</script>"))


def fake_status():
    return {"checked_at":"2026-10-29T13:00:00+00:00","services":[
        {"name":"Gateway","state":"running"},{"name":"Ollama","state":"ready"},
        {"name":"Publisher","state":"idle"}],
        "workers":[{"worker":"scout","job_id":"20261029T130000Z",
                    "stage":"generating","stale":False,"message":"Waiting for local agent response",
                    "updated_at":"2026-10-29T13:00:00+00:00"},
                   {"worker":"publisher","job_id":"20261029T123000Z",
                    "stage":"unknown","stale":True,"message":"No recent checkpoint",
                    "updated_at":"2026-10-29T12:30:00+00:00"}],
        "queue":{"available":True,"jobs":[{"kind":"comment","job_id":"a","state":"published",
                 "created":"2026-10-29T09:00:00+00:00","updated":"2026-10-29T09:00:00+00:00"}]}}


AT=datetime(2026,10,29,13,0,tzinfo=timezone.utc)


class OverviewTests(unittest.TestCase):
    def test_recorded_gauges_and_queue_totals_are_real(self):
        with tempfile.TemporaryDirectory() as folder:
            dbfile=Path(folder)/"bob.sqlite3"
            sample_db(dbfile)
            facts=overview.recorded(dbfile,at=AT)
            self.assertTrue(facts["available"])
            self.assertEqual(facts["limits"]["comment_daily"],8)
            self.assertEqual(facts["usage"],{"comments":3,"auto":1,"originals":1})
            q=facts["queues"]
            self.assertEqual((q["comments_queued"],q["manual_queued"],q["auto_queued"]),
                             (2,1,1))
            self.assertEqual(q["originals_draft"],2)
            self.assertEqual(q["originals_public_visible"],1)
            self.assertEqual(q["replies_observed"],2)
            self.assertEqual(q["comments_api_ack"],2)
            self.assertEqual(q["comments_uncertain"],1)
            self.assertEqual(q["generation_queued"],1)
            self.assertEqual(facts["next_possible_utc"]["comments"],
                             "2026-10-29T13:00:00+00:00")
            self.assertEqual(overview.pct(3,8),38)
            self.assertEqual(overview.pct(19,8),100)

    def test_readonly_missing_database_never_claims_zero_jobs(self):
        with tempfile.TemporaryDirectory() as folder:
            missing=Path(folder)/"missing.sqlite3"
            result=overview.recorded(missing,at=AT)
            self.assertFalse(result["available"])
            self.assertIsNone(result["usage"])
            self.assertIsNone(result["queues"])
            self.assertFalse(missing.exists())

    def test_budget_at_limit_has_utc_reset_not_guessed_schedule(self):
        at=datetime(2026,10,29,20,tzinfo=timezone.utc)
        slot=overview._next_possible(at,8,8,None,30)
        self.assertEqual(slot,"2026-10-30T00:00:00+00:00")

    def test_page_has_controls_and_escapes_event_text(self):
        with tempfile.TemporaryDirectory() as folder:
            dbfile=Path(folder)/"bob.sqlite3"
            sample_db(dbfile)
            with patch.object(overview,"live_status",side_effect=fake_status), \
                 patch.object(overview,"PAUSED",Path(folder)/"not-paused"):
                data=overview.snapshot(path=dbfile)
            html=overview.page(data)
            self.assertIn("<h1>Overview</h1>",html)
            self.assertIn("Daily activity budgets",html)
            self.assertIn("Queue &amp; publication",html)
            self.assertIn("Services &amp; dependencies",html)
            self.assertIn("Background workers",html)
            self.assertNotIn("Mission control",html)
            self.assertNotIn('class="bo-hero"',html)
            self.assertNotIn('class="bo-links"',html)
            self.assertNotIn("Gauges show daily attempts consumed",html)
            self.assertNotIn("These are local rate slots",html)
            self.assertIn('href="/manage?tab=activity&state=queued"',html)
            self.assertIn("3 / 8",html)
            self.assertIn("1 / 4",html)
            self.assertIn('src="/assets/bob-overview.js"',html)
            self.assertIn("&lt;script&gt;untrusted&lt;/script&gt;",html)
            self.assertNotIn("<script>untrusted</script>",html)
            self.assertIn('data-tone="busy">generating',html)
            self.assertIn('data-tone="quiet">unknown',html)
            self.assertIn("do not prove",html)

    def test_no_orphaned_hero_js_reference(self):
        javascript=overview.javascript()
        self.assertNotIn("id('health')", javascript)
        self.assertNotIn("chip.dataset.tone", javascript)
        self.assertNotIn("txt('updated'", javascript)
        self.assertIn("txt('metrics-state'",javascript)
        self.assertIn("services.replaceChildren()",javascript)
        self.assertIn("workers.replaceChildren()",javascript)

    def test_zero_auto_budget_is_disabled_not_unknown(self):
        ring=overview._cap("auto","Automatic",0,0,"Auto disabled","#6ee4d3")
        self.assertIn("Disabled",ring)
        self.assertIn("0 percent consumed",ring)
        self.assertIn("max === 0 ? 'Disabled'",overview.javascript())
        self.assertIn("txt('next-comment','Unknown')",overview.javascript())

    def test_navigation_and_sensitive_post_routes_are_unchanged(self):
        baseline, _=previous.build()
        changed,nav=candidate.build()
        def methods(code):
            cls=next(x for x in ast.parse(code).body if isinstance(x,ast.ClassDef) and x.name=="Handler")
            return {x.name:ast.dump(x,include_attributes=False)
                    for x in cls.body if isinstance(x,ast.FunctionDef)}
        a,b=methods(baseline),methods(changed)
        for method in ("do_POST","_change_password","_change_activity_limits",
                       "_handle_publication","_handle_original","_handle_manage_bulk",
                       "_valid_origin","_authenticated"):
            self.assertEqual(a[method],b[method],method)
        self.assertIn(b'elif self.path == "/api/dashboard/overview":',changed)
        self.assertIn(b'elif urlsplit(self.path).path == "/scout":',changed)
        self.assertIn(b'("/", "Overview", "Live overview")',nav)
        self.assertIn(b'("/scout", "Scout & review", "Scout and review")',nav)
        self.assertNotIn(b'("/", "Scout & review", "Scout and review")',nav)

    def test_javascript_safe_polling_only_when_visible(self):
        js=overview.javascript()
        self.assertIn("fetch('/api/dashboard/overview'",js)
        self.assertIn("setInterval(refresh,15000)",js)
        self.assertIn("document.hidden",js)
        self.assertIn("textContent",js)
        self.assertNotIn("innerHTML",js)
        self.assertIn("stale",js)
        self.assertIn("prefers-reduced-motion",overview.STYLE)


if __name__=="__main__":
    unittest.main()
