"""OC2 offline acceptance: synchronized existing toggles and honest automation
inventory with no new control authority; compact OC1 status regression."""
from __future__ import annotations
import ast
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for folder in ("scripts","src/lib/bob","webui"):
    sys.path.insert(0,str(ROOT/folder))
import bob_automation_center as auto
import bob_overview as overview
import build_v075_fm32d_candidate as before
import build_v076_oc2_candidate as after

OBS={
 "checked_at":"2026-10-30T14:20:00+00:00","paused":False,
 "services":[
  {"name":"Gateway","state":"running"},
  {"name":"Scout timer","state":"running"},
  {"name":"Publisher timer","state":"running"},
  {"name":"Ollama","state":"ready"}],
 "workers":[{"worker":"scout","stage":"completed",
             "updated_at":"2026-10-30T14:15:00+00:00"}],
 "metrics":{"available":True,"queues":{"comments_queued":6,
              "manual_queued":6,"auto_queued":0}},
 "operations":{"lanes":[
  {"key":"scout","next_scheduled":"Fri 2026-10-30 14:35:00 UTC"},
  {"key":"publisher","next_scheduled":"Fri 2026-10-30 14:40:00 UTC"},
  {"key":"original","next_scheduled":""},
  {"key":"dependencies","next_scheduled":""}]}
}
LOCAL={
 "available":True,"auto":True,"friends":False,
 "events":{"auto_enabled":"2026-10-30T11:00:00Z",
           "bob_friend_scout_setting":"2026-10-30T10:00:00Z"},
 "comment":{"state":"queued","at":"2026-10-30T14:10:00Z"},
 "auto_comment":None,"original":None,"draft":None,"focus":None,"interest":None
}

def fixture(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT)")
        db.execute("INSERT INTO publish_settings VALUES('auto_enabled','1')")
        db.execute("INSERT INTO publish_settings VALUES('bob_friend_scout_enabled','0')")
        db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY,at TEXT,kind TEXT)")
        db.execute("INSERT INTO publish_events VALUES(1,'2026-10-30T12:00:00Z','auto_enabled')")
        db.execute("INSERT INTO publish_events VALUES(2,'2026-10-30T13:00:00Z','bob_friend_scout_setting')")
        db.execute("CREATE TABLE publish_jobs(run_id TEXT,state TEXT,mode TEXT,updated_at TEXT)")
        db.execute("INSERT INTO publish_jobs VALUES('a','queued','manual','2026-10-30T13:10:00Z')")
        db.execute("CREATE TABLE original_posts(id TEXT,state TEXT,updated_at TEXT)")
        db.execute("CREATE TABLE original_requests(id TEXT,state TEXT,created_at TEXT)")
        db.execute("CREATE TABLE bob_friend_focus_jobs(id TEXT,status TEXT,updated_at TEXT)")
        db.execute("INSERT INTO bob_friend_focus_jobs VALUES('a','completed','2026-10-30T13:02:00Z')")

class AutomationTests(unittest.TestCase):
    def test_readonly_database_settings_and_activity(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"queue.sqlite3"
            fixture(path)
            result=auto._db_data(path)
            self.assertTrue(result["available"])
            self.assertTrue(result["auto"])
            self.assertFalse(result["friends"])
            self.assertEqual(result["comment"]["state"],"queued")
            self.assertEqual(result["focus"]["state"],"completed")
            self.assertEqual(result["events"]["bob_friend_scout_setting"],
                             "2026-10-30T13:00:00Z")
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0],1)
                self.assertEqual(db.execute("SELECT value FROM publish_settings WHERE name='auto_enabled'").fetchone()[0],"1")

    def test_missing_database_disables_all_write_forms(self):
        with tempfile.TemporaryDirectory() as temp:
            local=auto._db_data(Path(temp)/"absent.sqlite3")
            self.assertFalse(local["available"])
            self.assertIsNone(local["auto"])
            self.assertIsNone(local["friends"])
            html=auto.page("csrf",lambda t,b,p:b,observed=OBS,local=local)
            self.assertNotIn('<form class="oca-action"',html)
            self.assertIn("Saved toggle state is unknown",html)

    def test_inventory_shows_real_modes_distinct_from_timers(self):
        registry=auto.inventory(OBS,LOCAL)
        ids=[r["key"] for r in registry]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertIn("auto",ids)
        self.assertIn("friends",ids)
        self.assertIn("reply",ids)
        self.assertIn("original",ids)
        auto_row=next(r for r in registry if r["key"]=="auto")
        self.assertEqual(auto_row["state"],"on")
        self.assertEqual(auto_row["scheduled"],"Fri 2026-10-30 14:40:00 UTC")
        self.assertIn("manual replies have priority",auto_row["summary"])
        original=next(r for r in registry if r["key"]=="original")
        self.assertEqual(original["state"],"manual")
        self.assertEqual(original["scheduled"],"Not scheduled by this setting")
        self.assertNotIn("Enable",original["summary"])
        paused=auto.inventory({**OBS,"paused":True},LOCAL)
        self.assertEqual(next(r for r in paused if r["key"]=="auto")["state"],"paused")
        self.assertEqual(next(r for r in paused if r["key"]=="friends")["state"],"off")

    def test_only_existing_guarded_toggle_post_paths_and_confirmations(self):
        html=auto.page("csrf-<token>",lambda t,b,p:b,observed=OBS,local=LOCAL)
        self.assertIn('action="/autopost/disable"',html)
        self.assertIn('action="/moltbook/friend-scout"',html)
        self.assertEqual(html.count('<form class="oca-action"'),2)
        self.assertIn("ENABLE FRIEND SCOUTING",html)
        self.assertIn('name="expected" value="0"',html)
        self.assertIn('name="enabled" value="1"',html)
        self.assertNotIn("action=\"/automation",html)
        self.assertIn("csrf-&lt;token&gt;",html)
        self.assertNotIn("csrf-<token>",html)
        self.assertNotIn("Run now",html)
        flipped={**LOCAL,"auto":False,"friends":True}
        html2=auto.page("safe",lambda t,b,p:b,observed=OBS,local=flipped)
        self.assertIn('action="/autopost/enable"',html2)
        self.assertIn("ENABLE AUTO",html2)
        self.assertIn('name="expected" value="1"',html2)
        self.assertIn('name="enabled" value="0"',html2)
        self.assertIn('name="confirmation" value=""',html2)

    def test_category_view_compact_and_escaped_state(self):
        html=auto.page("csrf",lambda t,b,p:b,params={"view":["discovery"]},
                       observed=OBS,local=LOCAL)
        self.assertIn("<h2>Scout &amp; social discovery</h2>",html)
        self.assertNotIn("<h2>Posting &amp; replies</h2>",html)
        bad={**LOCAL,"events":{"auto_enabled":"<script>alert(1)</script>"}}
        html=auto.page("csrf",lambda t,b,p:b,params={"view":["posting"]},
                       observed=OBS,local=bad)
        self.assertNotIn("<script>alert",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("<details><summary>Details &amp; controls</summary>",html)
        self.assertIn("@media(max-width:470px)",auto.STYLE)

    def test_malformed_saved_toggle_disables_just_its_action(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"queue.sqlite3"
            fixture(path)
            with sqlite3.connect(path) as db:
                db.execute("UPDATE publish_settings SET value='garbage' WHERE name='auto_enabled'")
            local=auto._db_data(path)
            self.assertIsNone(local["auto"])
            self.assertFalse(local["friends"])
            html=auto.page("csrf",lambda t,b,p:b,observed=OBS,local=local)
            self.assertEqual(html.count('<form class="oca-action"'),1)
            self.assertNotIn('action="/autopost/',html)

    def test_manager_only_changes_authenticated_get_and_navigation(self):
        old,oldmenu=before.build()
        new,menu=after.build()
        a,b=ast.parse(old),ast.parse(new)
        def methods(tree):
            handler=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="Handler")
            return {n.name:ast.dump(n,include_attributes=False)
                    for n in handler.body if isinstance(n,ast.FunctionDef)}
        oldmethods,newmethods=methods(a),methods(b)
        self.assertEqual(oldmethods["do_POST"],newmethods["do_POST"])
        for method in ("_handle_publication","_save_friend_scout","_handle_original",
                       "_valid_host","_valid_origin","_authenticated"):
            self.assertEqual(oldmethods[method],newmethods[method],method)
        self.assertIn(b'elif urlsplit(self.path).path == "/automation":',new)
        self.assertIn(b'parse_qs(urlsplit(self.path).query[:128]',new)
        self.assertIn(b'("/automation", "Automation",',menu)
        self.assertNotIn(b'("/automation", "Automation",',oldmenu)
        self.assertLess(new.index(b'if not self._authenticated()'),
                        new.index(b'elif urlsplit(self.path).path == "/automation"'))
        self.assertNotIn(b'if path == "/automation":',new)

    def test_compact_overview_keeps_details_but_collapses_them(self):
        ops={"state":"waiting","headline":"Not sending","detail":"Detailed reason",
             "checked_at":"2026-10-30T14:20:00Z",
             "lanes":[{"key":"publisher","state":"waiting","activity":"6 comments queued",
                       "reason":"No active send confirmed","next_scheduled":""}]}
        html=overview._operations_html({"operations":ops})
        self.assertIn('<details class="bo-now-why">',html)
        self.assertIn("Why / evidence</summary>",html)
        self.assertIn("6 comments queued",html)
        self.assertIn("No active send confirmed",html)
        self.assertIn('id="bo-now-detail"',html)
        self.assertNotIn("<details open",html)
        js=overview.javascript()
        self.assertIn("summary.textContent='Why / evidence'",js)
        self.assertIn("detail.open=expanded.has(key)",js)
        self.assertIn("querySelectorAll('.bo-now-lane[data-key] details[open]')",js)
        self.assertNotIn("innerHTML",js)
        self.assertIn("setInterval(refresh,15000)",js)


if __name__=="__main__":
    unittest.main()
