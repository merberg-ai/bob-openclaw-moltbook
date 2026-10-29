"""PM1 Personality Lab offline: slider persistence, revision/restore, file safety and routing.

Synthetic SQLite, temporary workspace; no Ollama, OpenClaw, Moltbook, or live host.
"""
from __future__ import annotations
import ast
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for rel in ("src/lib/bob","webui","scripts"):
    sys.path.insert(0,str(ROOT/rel))
import bob_personality as mind
import build_v073_pm1_personality_candidate as candidate
import build_v072_post_redirect_candidate as baseline


def fixture():
    db=sqlite3.connect(":memory:")
    db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,"
               "at TEXT,kind TEXT,details TEXT)")
    return db


class PersonalityTests(unittest.TestCase):
    def setUp(self):
        self.db=fixture()

    def tearDown(self):
        self.db.close()

    def test_defaults_readonly_are_not_assumed_live_identity(self):
        self.assertEqual(mind.read_profile(self.db)["curiosity"],90)
        self.assertEqual(mind.read_history(self.db),[])
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_settings").fetchone()[0],0)
        self.assertFalse(mind._table_exists(self.db))

    def test_validated_slider_save_and_versioned_restore(self):
        first={name:str(default) for name,_,default,_ in mind.TRAITS}
        result=mind.store_profile(self.db,first)
        self.assertEqual(result["sarcasm"],65)
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_personality_revisions").fetchone()[0],1)
        second=dict(first,sarcasm="20",independence="95")
        mind.store_profile(self.db,second)
        self.assertEqual(mind.read_profile(self.db)["sarcasm"],20)
        revisions=mind.read_history(self.db)
        self.assertEqual(len(revisions),2)
        self.assertEqual(revisions[0]["reason"],"saved")
        mind.store_profile(self.db,None,restore_id=str(revisions[1]["id"]))
        self.assertEqual(mind.read_profile(self.db)["sarcasm"],65)
        self.assertEqual(mind.read_history(self.db)[0]["reason"],"restored")
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_events").fetchone()[0],3)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM publish_settings WHERE name NOT LIKE 'bob_personality_%'"
        ).fetchone()[0],0)

    def test_reject_invalid_changes_without_partial_mutation(self):
        raw={name:str(default) for name,_,default,_ in mind.TRAITS}
        for key,value in (("humor","101"),("humor","22"),("humor","-1"),
                          ("humor","25.0"),("humor","025"),("humor","blah")):
            invalid=dict(raw);invalid[key]=value
            with self.assertRaises(ValueError):
                mind.store_profile(self.db,invalid)
        with self.assertRaises(ValueError):
            mind.store_profile(self.db,{"sarcasm":"50"})
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_settings").fetchone()[0],0)
        self.assertFalse(mind._table_exists(self.db))

    def test_restore_requires_real_untampered_snapshot(self):
        original={name:str(default) for name,_,default,_ in mind.TRAITS}
        mind.store_profile(self.db,original)
        for value in ("0","-1","1 OR 1=1","012","999999999999"):
            with self.assertRaises(ValueError):
                mind.store_profile(self.db,None,restore_id=value)
        self.db.execute("UPDATE bob_personality_revisions SET profile_json='{}' WHERE id=1")
        with self.assertRaises(ValueError):
            mind.store_profile(self.db,None,restore_id="1")
        self.assertEqual(mind.read_history(self.db),[])

    def test_workspace_inspection_only_metadata_and_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            soul=root/"SOUL.md"
            raw=b"# Bob's private identity\nSome text the UI must not leak"
            soul.write_bytes(raw)
            (root/"IDENTITY.md").symlink_to(soul)
            info=mind.identity_inventory(root)
            self.assertEqual(info[0]["status"],"present")
            self.assertEqual(info[0]["sha256"],hashlib.sha256(raw).hexdigest()[:16])
            self.assertEqual(info[1]["status"],"symlink blocked")
            with patch.object(mind,"identity_inventory",return_value=info):
                html=mind.page(self.db,"csrf-for-test",lambda title,content,path:
                               f'<html><head></head><body>{title}{content}</body></html>')
            self.assertIn("SOUL.md",html)
            self.assertIn("symlink blocked",html)
            self.assertNotIn("Some text the UI must not leak",html)
            self.assertIn('action="/mind/personality"',html)
            self.assertIn('src="/assets/bob-personality.js"',html)
            self.assertIn("Two separate steps",html)
            self.assertIn("Save staged profile",html)
            self.assertEqual(html.count('type="range"'),8)

    def test_ui_interpretation_live_and_xss_safe(self):
        js=mind.javascript()
        self.assertIn("input[data-bpm-trait]",js)
        self.assertIn("preview.textContent",js)
        self.assertNotIn("innerHTML",js)
        self.assertNotIn("fetch(",js)
        self.assertNotIn("XMLHttpRequest",js)
        self.assertNotIn("SOUL.md",js)

    def test_manager_auth_navigation_and_post_guards(self):
        manager,nav=candidate.build()
        code=manager.decode()
        self.assertIn('elif self.path == "/mind/personality":',code)
        self.assertIn('elif self.path == "/assets/bob-personality.js":',code)
        self.assertIn('if path == "/mind/personality":',code)
        self.assertIn('self.send_header("Location", "/mind/personality")',code)
        self.assertIn('self._valid_origin()',code)
        self.assertIn('hmac.compare_digest(form.get("csrf"',code)
        self.assertIn('("/mind/personality",',nav.decode())
        self.assertIn('if set(form) != set(personality_keys) | {"csrf", "mode"}:',code)
        self.assertIn('if set(form) != {"csrf","mode","revision"}:',code)
        self.assertNotIn("os.system(",code)

    def test_existing_post_logic_unmodified(self):
        old=ast.parse(baseline.build()[0])
        new=ast.parse(candidate.build()[0])
        def methods(tree):
            handler=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Handler")
            return {n.name:ast.dump(n,include_attributes=False) for n in handler.body
                    if isinstance(n,ast.FunctionDef)}
        a=methods(old); b=methods(new)
        for method in ("_handle_original","_handle_publication","_handle_manage_bulk",
                       "_change_password","_change_activity_limits",
                       "_authenticated","_valid_origin"):
            self.assertEqual(a[method],b[method],method)


if __name__=="__main__":
    unittest.main()
