"""Focused offline tests of worker-enforced Activity Limits and Settings separation.

Synthetic SQLite only, no Moltbook network, no services or live credentials.
"""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import sqlite3
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_activity_limits as limits
import build_v072_activity_limits_candidate as candidate
import build_v072_compact_candidate as before


def fixture():
    db=sqlite3.connect(":memory:")
    db.execute("CREATE TABLE publish_settings (name TEXT PRIMARY KEY, value TEXT)")
    db.execute("CREATE TABLE publish_jobs (run_id TEXT PRIMARY KEY, mode TEXT, attempted_at TEXT)")
    db.execute("CREATE TABLE original_posts (id TEXT PRIMARY KEY, attempted_at TEXT)")
    db.execute("CREATE TABLE publish_events (at TEXT, kind TEXT, details TEXT)")
    return db


def insert_comment(db,index,mode,at):
    db.execute("INSERT INTO publish_jobs VALUES (?,?,?)",
               ("20261029T%02d0000Z" % index,mode,at))


def insert_original(db,index,at):
    db.execute("INSERT INTO original_posts VALUES (?,?)",(str(index),at))


AT=datetime(2026,10,29,14,0,tzinfo=timezone.utc)
RECOMMENDED={k:str(v) for k,v in limits.RECOMMENDED.items()}


class ActivityLimitsTests(unittest.TestCase):
    def setUp(self):
        self.db=fixture()

    def tearDown(self):
        self.db.close()

    def test_missing_settings_preserve_conservative_behavior(self):
        current=limits.read_limits(self.db)
        self.assertEqual((current["comment_daily"],current["comment_gap_minutes"],
                          current["comment_auto_daily"],current["original_daily"]),
                         (2,60,2,1))
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_settings").fetchone()[0],0)
        insert_comment(self.db,1,"manual","2026-10-29T13:30:00+00:00")
        self.assertFalse(limits.allowed(self.db,"comment",mode="auto",at=AT)[0])
        insert_comment(self.db,2,"auto","2026-10-29T12:00:00+00:00")
        self.assertIn("daily",limits.allowed(self.db,"comment",mode="manual",at=AT)[1])

    def test_recommended_budget_and_manual_auto_priority_counters(self):
        values=limits.save_limits(self.db,RECOMMENDED)
        self.assertEqual(values,limits.RECOMMENDED)
        for idx,hour in enumerate((10,11,12),1):
            insert_comment(self.db,idx,"auto",f"2026-10-29T{hour}:00:00+00:00")
        permitted,why=limits.allowed(self.db,"comment",mode="auto",at=AT)
        self.assertFalse(permitted)
        self.assertIn("automatic",why)
        self.assertEqual(limits.allowed(self.db,"comment",mode="manual",at=AT),(True,""))
        self.assertEqual(limits.summary(self.db,at=AT)["auto_used"],3)
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_events").fetchone()[0],1)

    def test_original_posts_respect_both_spacing_and_daily_budget(self):
        limits.save_limits(self.db,RECOMMENDED)
        insert_original(self.db,1,"2026-10-29T13:00:00+00:00")
        self.assertIn("interval",limits.allowed(self.db,"original",at=AT)[1])
        self.assertEqual(limits.allowed(
            self.db,"original",at=datetime(2026,10,29,15,30,tzinfo=timezone.utc)),(True,""))
        insert_original(self.db,2,"2026-10-29T11:00:00+00:00")
        self.assertIn("daily",limits.allowed(self.db,"original",at=AT)[1])

    def test_invalid_change_fails_before_any_setting_writes(self):
        original=dict(RECOMMENDED)
        for field,bad in (("comment_daily","21"),
                          ("comment_auto_daily","7"),
                          ("original_gap_minutes","0"),
                          ("comment_daily","01"),
                          ("comment_daily","2.5")):
            broken=dict(original)
            broken[field]=bad
            with self.assertRaises(ValueError):
                limits.save_limits(self.db,broken)
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_settings").fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_events").fetchone()[0],0)
        # A corrupt persisted setting must not allow unbounded sends.
        self.db.execute("INSERT INTO publish_settings VALUES (?,?)",
                        ("activity_limit_comment_daily","999"))
        with self.assertRaises(ValueError):
            limits.allowed(self.db,"comment",mode="manual",at=AT)

    def test_preview_does_not_save_limits_or_enable_autonomy(self):
        self.db.execute("INSERT INTO publish_settings VALUES ('auto_enabled','0')")
        html=limits.activity_page(self.db,"test-csrf",lambda t,s,r:s,preview=True)
        self.assertIn('name="comment_daily"',html)
        self.assertIn('value="6" selected',html)
        self.assertIn('value="45" selected',html)
        self.assertIn('value="3" selected',html)
        self.assertIn('name="confirmation"',html)
        self.assertIn("APPLY LIMITS",html)
        self.assertEqual(self.db.execute("SELECT value FROM publish_settings WHERE name='auto_enabled'").fetchone()[0],"0")
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM publish_settings WHERE name LIKE 'activity_limit_%'").fetchone()[0],0)

    def test_users_navigation_preserves_password_form(self):
        source=('<html><head><title>Settings</title></head><body>'
                '<section class="card bob-settings"><form method="post" '
                'action="/settings/password">'
                '<input name="csrf" value="original-hash"></form></section>'
                '</body></html>')
        result=limits.users_page(lambda:source)
        self.assertIn('href="/settings/users" aria-current="page"',result)
        self.assertEqual(result.count('action="/settings/password"'),1)
        self.assertIn('value="original-hash"',result)
        self.assertTrue(result.index('</head>') < result.index('class="bal"'))

    def test_builder_preserves_existing_sensitive_routes_and_workers(self):
        prior=ast.parse(before.build()[0])
        current,nav=candidate.build()
        updated=ast.parse(current)
        def methods(tree):
            cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Handler")
            return {x.name:ast.dump(x,include_attributes=False) for x in cls.body
                    if isinstance(x,ast.FunctionDef)}
        prev,new=methods(prior),methods(updated)
        for name in ("_authenticated","_valid_origin","_change_password",
                     "_handle_publication","_handle_original","_handle_manage_bulk"):
            self.assertEqual(prev[name],new[name],name)
        self.assertIn(b'elif self.path == "/settings/users":',current)
        self.assertIn(b'if path == "/settings/activity-limits":',current)
        self.assertIn(b'def _change_activity_limits(self):',current)
        self.assertIn(b'max_num_fields=12',current)
        publisher=(ROOT/"src/bin/bob-moltbook-publisher").read_bytes()
        original=(ROOT/"src/bin/bob-original-worker").read_bytes()
        self.assertIn(b'activity_allowed(db, "comment", mode=mode)',publisher)
        self.assertIn(b'activity_allowed(db, "original")',original)
        self.assertIn(b"state='sending'",publisher)
        self.assertIn(b"state='sending'",original)


if __name__=="__main__":
    unittest.main()
