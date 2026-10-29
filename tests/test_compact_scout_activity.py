"""Small offline acceptance for compact Scout/Activity page rendering.

Uses synthetic in-memory SQLite. No live systemd, credentials or Moltbook API.
"""
from __future__ import annotations

import ast
from html import escape
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))
sys.path.insert(0,str(ROOT / "src/lib/bob"))
import bob_dashboard_compact as compact
import bob_dashboard_manage as manage
import bob_originals
import build_v072_compact_candidate as builder
import build_v072_dashboard_manage_candidate as prior


def database():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE decisions(run_id TEXT PRIMARY KEY, draft_sha256 TEXT, status TEXT, decided_at TEXT)")
    db.execute("CREATE TABLE publish_jobs (run_id TEXT PRIMARY KEY, mode TEXT, state TEXT, draft_comment TEXT, created_at TEXT, post_id TEXT, comment_id TEXT)")
    db.execute("CREATE TABLE publish_settings (name TEXT PRIMARY KEY, value TEXT)")
    db.execute("CREATE TABLE published_replies (id TEXT PRIMARY KEY, post_id TEXT, comment_id TEXT, author TEXT, content TEXT, detected_at TEXT)")
    db.execute("CREATE TABLE publish_events (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, kind TEXT, details TEXT)")
    bob_originals.initialize(db)
    manage.initialize(db)
    return db


def fake_status(record, decisions):
    value = decisions.get(record["run_id"])
    if value and value[0] == record["approval_sha256"]:
        return value[1]
    return "pending" if record["verified_draft"] else "needs review"


def record(index):
    rid = "20261029T%02d0000Z" % index
    return {
        "run_id": rid, "approval_sha256": manage.fingerprint("draft",rid),
        "verified_draft": True, "status": "pending", "chosen_title": "Draft %02d" % index,
        "chosen_author": "a <b>not HTML</b>", "why": "An interesting question",
        "draft_comment": "Synthetic text " + str(index), "validation_errors": []
    }


def fake_wrap(title, body, route):
    return body


class CompactDashboardTests(unittest.TestCase):
    def setUp(self):
        self.db = database()
        self.records = [record(i) for i in range(14)]

    def tearDown(self):
        self.db.close()

    def test_scout_pending_defaults_to_eight_compact_cards(self):
        rid = self.records[0]["run_id"]
        self.db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?,?,?)",
                        (rid,"auto","queued","Auto queued","2026-10-29T00:00Z","test",None))
        html = compact.scout_page(self.db,self.records,fake_status,{},"csrf-only",fake_wrap)
        self.assertEqual(html.count('<article class="bcv-card"'),8)
        self.assertIn("Page 1 of 2",html)
        self.assertIn("Publication: queued (auto)",html)
        self.assertIn('action="/review/'+rid+'/approve"',html)
        self.assertIn('href="/scout/full#run-'+rid+'"',html)
        self.assertIn("a &lt;b&gt;not HTML&lt;/b&gt;",html)
        self.assertNotIn("a <b>not HTML</b>",html)
        self.assertIn('name="csrf" value="csrf-only"',html)

    def test_archived_scout_not_erased_or_implicitly_published(self):
        rid = self.records[0]["run_id"]
        self.db.execute("INSERT INTO dashboard_hidden VALUES (?,?,?)",
                        ("scout",rid,"2026-10-29T00:00Z"))
        active = compact.scout_page(self.db,self.records,fake_status,
                                    {"show":["active"]},"csrf",fake_wrap)
        archived = compact.scout_page(self.db,self.records,fake_status,
                                      {"show":["archived"]},"csrf",fake_wrap)
        self.assertNotIn('<article class="bcv-card" id="run-'+rid+'"',active)
        self.assertIn('<article class="bcv-card" id="run-'+rid+'"',archived)
        self.assertIn("1 pending archived",active)
        self.assertEqual(self.db.execute("SELECT count(*) FROM decisions").fetchone()[0],0)

    def test_activity_tabs_show_eight_items_and_careful_public_claims(self):
        for i in range(13):
            self.db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?,?,?)",
                            ("20261029T%02d0000Z"%i,"manual","published",
                             "A simulated posted comment","2026-10-29T12:00Z",None,None))
        result=compact.activity_page(self.db,{},fake_wrap)
        self.assertIn("Comments (13)",result)
        self.assertIn("Incoming replies (0)",result)
        self.assertEqual(result.count('<article class="bcv-card"'),8)
        self.assertIn("API acknowledged; public visibility not independently confirmed",result)
        self.assertIn("Page 1 of 2",result)

    def test_activity_reply_escapes_untrusted_text_and_is_section_scoped(self):
        self.db.execute("INSERT INTO published_replies VALUES (?,?,?,?,?,?)",
                        ("synthetic","unknown","comment","<script>alert(1)</script>",
                         "<img src=x onerror=alert(1)>","2026-10-29T01:00Z"))
        reply = compact.activity_page(self.db,{"view":["replies"]},fake_wrap)
        self.assertIn("&lt;script&gt;",reply)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;",reply)
        self.assertNotIn("<script>alert(1)</script>",reply)
        self.assertNotIn('<article class="bcv-card"',compact.activity_page(
            self.db,{"view":["events"]},fake_wrap))

    def test_builder_preserves_all_existing_post_routes(self):
        existing = ast.parse(prior.build()[0])
        changed_code,nav = builder.build()
        changed = ast.parse(changed_code)
        def methods(tree):
            cls = next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="Handler")
            return {n.name:ast.dump(n,include_attributes=False)
                    for n in cls.body if isinstance(n,ast.FunctionDef)}
        older, newer = methods(existing),methods(changed)
        for name in ("do_POST","_handle_manage_bulk","_handle_publication",
                     "_handle_original","_valid_origin","_authenticated"):
            self.assertEqual(older[name],newer[name],name)
        self.assertIn(b'elif self.path == "/scout/full":',changed_code)
        self.assertIn(b'elif self.path == "/activity/full":',changed_code)
        self.assertIn(b'("/manage", "Manage queues", "Manage queues")',nav)
        self.assertEqual(len(manage.ALLOWED["activity"]),2)
        self.assertEqual(manage.get_items(self.db,"scout",self.records,fake_status)[0]["detail"],
                         "/scout/full#run-"+self.records[0]["run_id"])


if __name__ == "__main__":
    unittest.main()
