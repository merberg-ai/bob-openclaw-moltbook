"""FM3.1 friend-specific private watch preferences and sourced interest history.

Exercises existing Activity Manager POST contract (six fields), local SQLite
state and readonly Scout selection. No network, timers, credentials or posts.
"""
from __future__ import annotations
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))

import bob_friends as friends
import bob_friend_scout as scout
import bob_publish_common as common

RID="20261029T214411Z"
PID="01234567-89ab-cdef-0123-456789abcdef"


def fields(relation="interesting"):
    return dict(display_name="Local Agent",relationship=relation,
                interests="Local AI and astronomy",notes="Secret operator notes stay local")


def init_db(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT)")
        db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT, "
                   "at TEXT,kind TEXT,details TEXT)")
        friends.create(db,"FriendOne",fields("friend"))
        friends.create(db,"FriendTwo",fields("interesting"))
        friends.create(db,"FriendThree",fields("acquaintance"))


def post_source(root):
    payload={"posts":[{"id":PID,"title":"How agent memory changes communities",
                       "author":"FriendOne","content":"An interesting debate"}]}
    raw=json.dumps(payload).encode()
    (root/("scout-feed-"+RID+".json")).write_bytes(raw)
    snapshot_hash=hashlib.sha256(raw).hexdigest()
    draft="This discussion makes me think about memory."
    record=dict(schema=2,run_id=RID,status="pending",snapshot_sha256=snapshot_hash,
         snapshot_file="scout-feed-"+RID+".json",chosen_post_id=PID,
         chosen_title="How agent memory changes communities",
         chosen_author="FriendOne",
         why="I find the implications of persistent memory for shared agency fascinating.",
         draft_comment=draft,
         draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),
         approval_sha256=hashlib.sha256((PID+"\n"+draft+"\n"+snapshot_hash).encode()).hexdigest())
    (root/("scout-result-"+RID+".json")).write_text(json.dumps(record))
    return record


def toggle_form(friend,watch_sha,new):
    return dict(csrf="test",operation="watch",id=friend["id"],
                friend_sha=friend["sha256"],watch_sha=watch_sha,
                watch_enabled=str(new))


class FM31Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.dbpath=self.root/"activity-queue.sqlite3"
        init_db(self.dbpath)
        self.p1=patch.object(common,"DB",self.dbpath)
        self.p2=patch.object(common,"DATA",self.root)
        self.p1.start()
        self.p2.start()
        self.addCleanup(self.p1.stop)
        self.addCleanup(self.p2.stop)

    def db(self):
        return sqlite3.connect(self.dbpath)

    def friend(self,handle):
        with self.db() as db:
            ident=db.execute("SELECT id FROM bob_friends WHERE handle=?",(handle,)).fetchone()[0]
            return friends._get(db,ident)

    def toggle(self,handle,on,sha="default"):
        friend=self.friend(handle)
        with self.db() as db:
            return scout.change(db,toggle_form(friend,sha,on))

    def test_default_on_preserves_existing_friend_scout_without_migration(self):
        # Existing hosts can run Scout with read-only DB before page creates
        # new preferences table.
        with self.db() as db:
            self.assertEqual(scout._preferences(db),{})
            self.assertFalse(scout.enabled(db))
            self.assertEqual(len(scout._watch(db)),3)
        self.assertEqual(scout.selected_watch(),[])
        with self.db() as db:
            scout.change(db,dict(csrf="x",enabled="1",expected="0",
                                 confirmation=scout.CONFIRM))
        selected=scout.selected_watch(date=date(2026,10,30))
        self.assertEqual(len(selected),2)
        self.assertTrue(all(x["watch_enabled"] for x in selected))
        self.assertEqual(len({x["id"] for x in selected}),2)

    def test_pause_and_resume_individual_watch_preserve_friends(self):
        with self.db() as db:
            scout.init_preferences(db)
        self.assertEqual(self.toggle("FriendOne",0),"0")
        with self.db() as db:
            watch={x["handle"]:x for x in scout._watch(db,include_disabled=True)}
            self.assertFalse(watch["FriendOne"]["watch_enabled"])
            self.assertTrue(watch["FriendTwo"]["watch_enabled"])
            self.assertEqual(len(scout._watch(db)),2)
            self.assertEqual(friends._get(db,self.friend("FriendOne")["id"])["state"],"active")
            first=watch["FriendOne"]["watch_sha"]
        with self.db() as db:
            scout.change(db,dict(csrf="x",enabled="1",expected="0",
                                 confirmation=scout.CONFIRM))
        selection=scout.selected_watch(date=date(2026,10,30))
        self.assertNotIn("FriendOne",[x["handle"] for x in selection])
        self.assertEqual(self.toggle("FriendOne",1,sha=first),"1")
        with self.db() as db:
            self.assertEqual(len(scout._watch(db)),3)
            states=db.execute("SELECT version,enabled FROM bob_friend_watch_history "
                              "WHERE friend_id=? ORDER BY version",
                              (self.friend("FriendOne")["id"],)).fetchall()
            self.assertEqual(states,[(1,0),(2,1)])
            events=[row[0] for row in db.execute("SELECT kind FROM publish_events")]
            self.assertIn("bob_friend_watch_changed",events)
            self.assertEqual(db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0],0) if (
                db.execute("SELECT 1 FROM sqlite_master WHERE name='publish_jobs'").fetchone()) else None

    def test_stale_double_click_and_invalid_preferences_block(self):
        with self.db() as db:
            scout.init_preferences(db)
            item=self.friend("FriendOne")
            with self.assertRaisesRegex(ValueError,"already selected"):
                scout.change(db,toggle_form(item,"default",1))
            with self.assertRaisesRegex(ValueError,"Invalid friend scouting form"):
                scout.change(db,{**toggle_form(item,"default",0),"irrelevant":"oops"})
            with self.assertRaisesRegex(ValueError,"Invalid friend scouting form"):
                scout.change(db,toggle_form(item,"default","wat"))
            with self.assertRaisesRegex(ValueError,"changed; reload"):
                scout.change(db,toggle_form(item,"wrong",0))
            scout.change(db,toggle_form(item,"default",0))
            with self.assertRaisesRegex(ValueError,"changed; reload"):
                scout.change(db,toggle_form(item,"default",1))
            with self.assertRaisesRegex(ValueError,"changed; reload"):
                scout.change(db,{**toggle_form(item,"default",1),"friend_sha":"0"*64})
            self.assertEqual(db.execute("SELECT count(*) FROM bob_friend_watch_history").fetchone()[0],1)

    def test_corrupted_pref_fail_closed_even_when_scout_enabled(self):
        with self.db() as db:
            scout.init_preferences(db)
            scout.change(db,toggle_form(self.friend("FriendOne"),"default",0))
            db.execute("UPDATE bob_friend_watch_prefs SET enabled=1 WHERE "
                       "friend_id=?",(self.friend("FriendOne")["id"],))
            active=scout._watch(db)
            self.assertNotIn("FriendOne",[x["handle"] for x in active])
            checked=next(x for x in scout._watch(db,include_disabled=True)
                         if x["handle"]=="FriendOne")
            self.assertTrue(checked["watch_problem"])
            with self.assertRaisesRegex(ValueError,"integrity failed"):
                scout.change(db,toggle_form(self.friend("FriendOne"),"default",1))
        html=scout.page(self.db().__enter__(),"csrf",lambda t,b,p:b,[]) if False else ""
        self.assertEqual(html,"")  # No ability to silently bypass a sealed record.

    def test_muted_and_archived_excluded_independent_of_pref(self):
        with self.db() as db:
            scout.init_preferences(db)
            a=self.friend("FriendOne")
            scout.change(db,toggle_form(a,"default",0))
            b=self.friend("FriendTwo")
            friends.change(db,b["id"],b["sha256"],"mute")
            c=self.friend("FriendThree")
            friends.change(db,c["id"],c["sha256"],"archive")
            self.assertEqual(scout._watch(db),[])
            self.assertEqual({x["handle"] for x in scout._watch(db,include_disabled=True)},
                             {"FriendOne"})
            with self.assertRaisesRegex(ValueError,"must be active"):
                scout.change(db,toggle_form(b,"default",0))

    def test_source_verified_bob_observations_are_readonly_and_escaped(self):
        rec=post_source(self.root)
        self.assertIsNotNone(common.load_record(RID))
        with self.db() as db:
            active=scout._watch(db,include_disabled=True)
            observations=scout.friend_observations([rec],active)
            self.assertEqual(len(observations),1)
            self.assertEqual(observations[0]["handle"],"FriendOne")
            self.assertIn("persistent memory",observations[0]["why"])
            self.assertNotIn("Secret operator notes",str(observations))
            html=scout.page(db,"test",lambda t,b,p:b,[rec])
            self.assertIn("Bob’s selected friend discussions",html)
            self.assertIn("persistent memory",html)
            self.assertNotIn("Secret operator notes",html)
            self.assertIn("Pause watching this friend",html)
            self.assertIn('name="operation" value="watch"',html)
            self.assertIn('name="watch_sha" value="default"',html)
        # Raw selected-record fields without verifiable original snapshot
        # must never be shown as Bob's observations.
        path=self.root/("scout-feed-"+RID+".json")
        path.write_text('{"posts":[]}')
        with self.db() as db:
            self.assertEqual(scout.friend_observations([rec],scout._watch(db,include_disabled=True)),[])
            html=scout.page(db,"test",lambda t,b,p:b,[rec])
            self.assertNotIn("persistent memory",html)

    def test_remote_why_html_is_escaped_not_assumed_instruction(self):
        rec=post_source(self.root)
        path=self.root/("scout-result-"+RID+".json")
        data=json.loads(path.read_text())
        data["why"]="<img src=x onerror=alert(1)>"
        path.write_text(json.dumps(data))
        with self.db() as db:
            html=scout.page(db,"test",lambda t,b,p:b,[data])
        self.assertIn("&lt;img",html)
        self.assertNotIn("<img src=x",html)

    def test_existing_optin_form_and_global_auto_permissions_unmodified(self):
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"Confirmation"):
                scout.change(db,dict(csrf="x",enabled="1",expected="0",confirmation="no"))
            scout.change(db,dict(csrf="x",enabled="1",expected="0",
                                 confirmation=scout.CONFIRM))
            self.assertTrue(scout.enabled(db))
            scout.change(db,dict(csrf="x",enabled="0",expected="1",confirmation=""))
            self.assertFalse(scout.enabled(db))
            self.assertEqual(db.execute("SELECT count(*) FROM bob_friend_watch_history").fetchone()[0],0)


if __name__=="__main__":
    unittest.main()
