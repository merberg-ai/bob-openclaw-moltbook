"""PM2.1 synthetic, offline memory acceptance. No host, OpenClaw or Moltbook."""
from __future__ import annotations
import ast
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for rel in ("src/lib/bob", "webui", "scripts"):
    sys.path.insert(0, str(ROOT / rel))

import bob_memory as mm
import build_v073_pm2_memory_candidate as candidate
import build_v073_pm1_apply_candidate as baseline


def fixture():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE decisions(run_id TEXT PRIMARY KEY,draft_sha256 TEXT,status TEXT,decided_at TEXT)")
    db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,"
               "at TEXT,kind TEXT,details TEXT)")
    db.execute("INSERT INTO decisions VALUES ('test','unchanged','approved','before')")
    return db


def fields(**kwargs):
    result = dict(title="Interesting discovery", content="Evidence is fallible; verify next time.",
                  category="observation", confidence="low",
                  source_label="Manually noted from a public discussion",
                  source_url="https://www.example.com/post/123")
    result.update(kwargs)
    return result


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.db = fixture()

    def tearDown(self):
        self.db.close()

    def current(self, ident):
        return mm._get(self.db, ident)

    def test_idempotent_schema_and_private_history_do_not_touch_publication(self):
        mm.initialize(self.db)
        mm.initialize(self.db)
        ident = mm.create(self.db, fields())
        row = self.current(ident)
        self.assertEqual(row["source_kind"], "operator")
        self.assertEqual(row["state"], "active")
        self.assertEqual(row["version"], 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memory_revisions").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT status FROM decisions WHERE run_id='test'").fetchone()[0], "approved")
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_settings").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT kind FROM publish_events").fetchone()[0], "bob_memory_created")

    def test_edit_correction_and_immutable_version_snapshots(self):
        ident = mm.create(self.db, fields())
        old = self.current(ident)
        mm.change(self.db, ident, old["sha256"], "edit", fields(
            content="Reviewed: the observation needs more context."), "Clarified source context")
        updated = self.current(ident)
        self.assertNotEqual(old["sha256"], updated["sha256"])
        self.assertEqual(updated["version"], 2)
        with self.assertRaisesRegex(ValueError, "changed"):
            mm.change(self.db, ident, old["sha256"], "archive")
        mm.change(self.db, ident, updated["sha256"], "correct", fields(
            content="Corrected: the earlier observation was false.",
            confidence="medium"), "Found contradictory evidence")
        records = self.db.execute(
            "SELECT version,action,snapshot_json FROM bob_memory_revisions "
            "WHERE memory_id=? ORDER BY version", (ident,)).fetchall()
        self.assertEqual([(r[0], r[1]) for r in records],
                         [(1, "create"), (2, "edit"), (3, "correct")])
        self.assertIn("fallible", records[0][2])
        self.assertIn("contradictory evidence", self.db.execute(
            "SELECT reason FROM bob_memory_revisions ORDER BY version DESC LIMIT 1").fetchone()[0])
        self.assertEqual(self.db.execute("SELECT status FROM decisions").fetchone()[0], "approved")

    def test_archive_exclude_restore_and_edit_guards(self):
        ident = mm.create(self.db, fields())
        mm.change(self.db, ident, self.current(ident)["sha256"], "exclude")
        self.assertEqual(self.current(ident)["state"], "excluded")
        with self.assertRaisesRegex(ValueError, "Restore"):
            mm.change(self.db, ident, self.current(ident)["sha256"], "edit",
                      fields(content="Never allowed"), "Changed while excluded")
        with self.assertRaises(ValueError):
            mm.change(self.db, ident, self.current(ident)["sha256"], "exclude")
        mm.change(self.db, ident, self.current(ident)["sha256"], "restore")
        mm.change(self.db, ident, self.current(ident)["sha256"], "archive")
        self.assertEqual(self.current(ident)["state"], "archived")
        mm.change(self.db, ident, self.current(ident)["sha256"], "restore")
        self.assertEqual(self.current(ident)["state"], "active")
        self.assertEqual(self.current(ident)["version"], 5)

    def test_reject_untrusted_urls_and_oversize_or_invalid_content(self):
        for url in ("http://example.com", "javascript:alert(1)", "https://localhost",
                    "https://127.0.0.1/private", "https://user:pass@example.com",
                    "https://example.com:1234/x", "https://example.com/\nheader"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                mm.create(self.db, fields(source_url=url))
        for bad in (dict(title="a"), dict(content=""), dict(content="a"*2401),
                    dict(source_label="too long "*30), dict(confidence="certain"),
                    dict(category="command"), dict(title="<\x00malformed>")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                mm.create(self.db, fields(**bad))
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memories").fetchone()[0], 0)

    def test_dispatch_requires_exact_bounded_fields(self):
        post = dict(fields(), csrf="dummy", operation="create")
        ident = mm.dispatch(self.db, post)
        self.assertEqual(self.current(ident)["version"], 1)
        with self.assertRaises(ValueError):
            mm.dispatch(self.db, dict(post, unexpected="ignored?"))
        with self.assertRaises(ValueError):
            mm.dispatch(self.db, dict(operation="edit", csrf="dummy", id=ident))
        with self.assertRaises(ValueError):
            mm.dispatch(self.db, {"operation":"delete", "csrf":"dummy", "id":ident})
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memories").fetchone()[0], 1)

    def test_render_escapes_memory_and_sources_and_shows_search_history(self):
        ident = mm.create(self.db, fields(
            title="Unexpected <script>alert(1)</script>",
            content="Quoted malicious input: <img src=x onerror=alert(1)>",
            source_label="<iframe>bad</iframe>"))
        html = mm.page(self.db, {"q":["Unexpected"], "show":["all"], "edit":[ident]},
                       "test-csrf", lambda title, body, path: body)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<iframe>bad</iframe>", html)
        self.assertIn("Open supplied source link", html)
        self.assertIn('rel="noopener noreferrer nofollow"', html)
        self.assertIn("Revision history", html)
        self.assertIn("Source description", html)
        self.assertIn("Correct", html)
        self.assertIn('name="expected_sha"', html)
        self.assertIn("operator-entered", html)
        self.assertNotIn("moltbook.com/api", html)

    def test_status_filters_and_optimistic_edit_ui(self):
        a = mm.create(self.db, fields(title="Alpha memory"))
        b = mm.create(self.db, fields(title="Bravo memory"))
        mm.change(self.db, b, self.current(b)["sha256"], "exclude")
        html = mm.page(self.db, {"show":["active"]}, "token", lambda t,c,p:c)
        self.assertIn("Alpha memory", html)
        self.assertNotIn("Bravo memory", html)
        html = mm.page(self.db, {"show":["excluded"],"edit":[b]}, "token", lambda t,c,p:c)
        self.assertIn("Bravo memory", html)
        self.assertIn("Restore to active", html)
        self.assertIn("Restore it to active before editing", html)
        self.assertEqual(mm._get(self.db,a)["state"],"active")

    def test_existing_auth_publish_handlers_unchanged(self):
        old, old_nav = baseline.build()
        new, nav = candidate.build()
        self.assertIn(b'elif urlsplit(self.path).path == "/mind/memory":',new)
        self.assertIn(b'if path == "/mind/memory":',new)
        self.assertIn(b'self._valid_origin()',new)
        self.assertIn(b'hmac.compare_digest(data.get("csrf"',new)
        self.assertIn(b'max_num_fields=12',new)
        self.assertIn(b'/mind/memory',nav)
        self.assertNotIn(b'/mind/memory',old_nav)
        self.assertIn(b'def _save_memory(self):',new)
        def methods(raw):
            tree=ast.parse(raw)
            cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Handler")
            return {n.name: ast.dump(n,include_attributes=False)
                    for n in cls.body if isinstance(n,ast.FunctionDef)}
        a,b=methods(old),methods(new)
        self.assertEqual(set(b)-set(a),{"_save_memory"})
        for name in ("_apply_personality","_save_personality","_handle_publication",
                     "_handle_original","_handle_manage_bulk","_authenticated",
                     "_valid_origin","_change_activity_limits"):
            self.assertEqual(a[name],b[name],name)
        compile(new, "bob-activity-manager", "exec")
        compile(nav, "navigation_shell.py", "exec")


if __name__ == "__main__":
    unittest.main()
