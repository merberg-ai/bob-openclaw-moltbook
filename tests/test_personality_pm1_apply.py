"""PM1 Apply acceptance: synthetic agent workspace and private SQLite only."""
from __future__ import annotations
import ast
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for p in ("src/lib/bob","scripts","webui"):
    sys.path.insert(0,str(ROOT/p))
import bob_personality_apply as app
import bob_personality as mind
import build_v073_pm1_apply_candidate as candidate
import build_v073_pm1_csp_candidate as before


def database():
    db=sqlite3.connect(":memory:")
    db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,kind TEXT,details TEXT)")
    return db


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.workspace=self.home/".openclaw/workspace"
        self.workspace.mkdir(parents=True)
        self.original=b"# Bob \xf0\x9f\x92\x80\n\nCurious, technical, independent-minded.\nNever disclose credentials.\n"
        (self.workspace/"SOUL.md").write_bytes(self.original)
        (self.workspace/"IDENTITY.md").write_text("Bob",encoding="utf-8")
        self.state=self.home/".local/state/bob-personality"
        self.db=database()
        self.addCleanup(self.db.close)
        self.home_patch=patch.object(app,"HOME",self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def prepare(self):
        return app.plan(self.db,resolver=lambda:self.workspace)

    def do_apply(self,p=None):
        p=p or self.prepare()
        return app.apply(self.db,p["before_sha"],p["profile_sha"],
                         "APPLY BOB",resolver=lambda:self.workspace,state=self.state)

    def test_managed_block_preserves_original_bytes_and_rolls_back(self):
        p=self.prepare()
        self.assertIn("+<!-- BOB_PERSONALITY_STYLE_V1_BEGIN -->",p["diff"])
        self.assertTrue(p["after"].startswith(self.original))
        result=self.do_apply(p)
        updated=(self.workspace/"SOUL.md").read_bytes()
        self.assertEqual(app.digest(updated),result["after"])
        self.assertIn(app.BEGIN.encode(),updated)
        self.assertEqual((self.state/(result["id"]+".soul")).read_bytes(),self.original)
        self.assertEqual((self.state/(result["id"]+".soul")).stat().st_mode & 0o777,0o600)
        self.assertTrue(self.state.stat().st_mode & 0o077 == 0)
        restored=app.rollback("ROLL BACK",result["after"],
                             resolver=lambda:self.workspace,state=self.state)
        self.assertEqual(restored["status"],"rolled_back")
        self.assertEqual((self.workspace/"SOUL.md").read_bytes(),self.original)
        with self.assertRaises(ValueError):
            app.rollback("ROLL BACK",result["after"],resolver=lambda:self.workspace,state=self.state)

    def test_reapply_replaces_only_managed_block(self):
        self.do_apply()
        old=(self.workspace/"SOUL.md").read_bytes()
        mind.store_profile(self.db,dict((k,str(15 if k=="sarcasm" else d))
                          for k,_,d,_ in mind.TRAITS))
        p=self.prepare()
        self.assertTrue(p["existing"])
        self.assertIn("- Sarcasm: minimal",p["after"].decode())
        self.assertEqual(p["after"].count(app.MARK_START),1)
        self.assertTrue(p["after"].startswith(self.original))
        self.do_apply(p)
        self.assertNotEqual(old,(self.workspace/"SOUL.md").read_bytes())

    def test_changed_soul_or_profile_refuses_before_file_write(self):
        p=self.prepare()
        (self.workspace/"SOUL.md").write_bytes(self.original+b"\nExternal author edit")
        with self.assertRaisesRegex(ValueError,"changed"):
            self.do_apply(p)
        self.assertIn(b"External author edit",(self.workspace/"SOUL.md").read_bytes())
        self.assertFalse((self.state/"last.json").exists())
        self.assertEqual(list(self.state.glob("*.soul")),[])
        (self.workspace/"SOUL.md").write_bytes(self.original)
        p=self.prepare()
        mind.store_profile(self.db,{k:str(10) for k in mind.KEYS})
        with self.assertRaisesRegex(ValueError,"changed"):
            self.do_apply(p)
        self.assertEqual((self.workspace/"SOUL.md").read_bytes(),self.original)

    def test_confirmations_and_unsafe_markers(self):
        p=self.prepare()
        with self.assertRaisesRegex(ValueError,"APPLY BOB"):
            app.apply(self.db,p["before_sha"],p["profile_sha"],"YES",
                      resolver=lambda:self.workspace,state=self.state)
        self.assertFalse(self.state.exists())
        for markers in (app.BEGIN,app.END,app.END+"\n"+app.BEGIN,
                        app.BEGIN+"\n"+app.BEGIN+"\n"+app.END):
            with self.subTest(markers=markers):
                (self.workspace/"SOUL.md").write_text(markers)
                with self.assertRaises(ValueError):
                    self.prepare()

    def test_symlinks_and_hardlinks_blocked(self):
        target=self.home/"real.md"
        target.write_bytes(self.original)
        soul=self.workspace/"SOUL.md"
        soul.unlink()
        soul.symlink_to(target)
        with self.assertRaises(ValueError):
            self.prepare()
        soul.unlink()
        soul.hardlink_to(target)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_cli_verifies_main_agent_and_rejects_unrelated_workspace(self):
        payload=json.dumps([{"id":"main","workspace":str(self.workspace)},
                            {"id":"research","workspace":str(self.home/"research")}])
        fake=SimpleNamespace(returncode=0,stdout=payload,stderr="")
        with patch.object(app.shutil,"which",return_value="/usr/bin/openclaw"), \
             patch.object(app.subprocess,"run",return_value=fake) as runner:
            self.assertEqual(app.agent_workspace(),self.workspace)
            self.assertEqual(runner.call_args.args[0][-3:],["agents","list","--json"])
        for data in ([],[{"id":"another","workspace":str(self.workspace)}],
                     [{"id":"main","workspace":"/etc"}]):
            with patch.object(app.shutil,"which",return_value="/usr/bin/openclaw"), \
                 patch.object(app.subprocess,"run",return_value=SimpleNamespace(
                     returncode=0,stdout=json.dumps(data),stderr="")):
                with self.assertRaises(ValueError):
                    app.agent_workspace()

    def test_panel_requires_verified_workspace_and_is_escaped(self):
        failed=app.panel(self.db,"token",resolver=lambda:(_ for _ in ()).throw(
            ValueError("not verified")),state=self.state)
        self.assertIn("Apply unavailable",failed)
        self.assertNotIn('name="expected_before"',failed)
        html=app.panel(self.db,"csrf",resolver=lambda:self.workspace,state=self.state)
        self.assertIn("Apply to Bob",html)
        self.assertIn("Current managed style",html)
        self.assertIn('name="expected_before"',html)
        self.assertIn("APPLY BOB",html)
        self.assertNotIn("Never disclose credentials",html)

    def test_confirmations_use_thematic_responsive_forms(self):
        html=app.panel(self.db,"synthetic-csrf",
                       resolver=lambda:self.workspace,state=self.state)
        self.assertIn('class="bpm-confirm"',html)
        self.assertIn('id="bpm-apply-confirm" type="text"',html)
        self.assertIn('name="confirmation" maxlength="20"',html)
        self.assertIn('.bpm-confirm input[type=text]',mind.CSS)
        self.assertIn('.bpm-confirm label,.bpm-confirm button',mind.CSS)
        self.do_apply()
        applied=app.panel(self.db,"synthetic-csrf",
                          resolver=lambda:self.workspace,state=self.state)
        self.assertIn('id="bpm-rollback-confirm" type="text"',applied)
        self.assertEqual(applied.count('class="bpm-confirm"'),2)

    def test_generated_manager_only_adds_guarded_new_actions(self):
        new,nav=candidate.build()
        old,old_nav=before.build()
        self.assertEqual(nav,old_nav)
        src=new.decode()
        for x in ('"/mind/personality/apply"','"/mind/personality/rollback"',
                  "self._valid_origin()","hmac.compare_digest(form.get(\"csrf\""):
            self.assertIn(x,src)
        def methods(src):
            tree=ast.parse(src)
            cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Handler")
            return {n.name:ast.dump(n,include_attributes=False) for n in cls.body
                    if isinstance(n,ast.FunctionDef)}
        a,b=methods(old),methods(new)
        for k in ("_handle_original","_handle_publication","_handle_manage_bulk",
                  "_save_personality","_change_activity_limits",
                  "_authenticated","_valid_origin"):
            self.assertEqual(a[k],b[k],k)
        self.assertIn("_apply_personality",b)


if __name__=="__main__":
    unittest.main()
