"""FM1 friends directory acceptance, isolated from live services and external APIs."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for p in ("src/lib/bob","webui","scripts"):
    sys.path.insert(0,str(ROOT/p))
import bob_publish_common as common
import bob_friends as friends
import build_v074_fm1_friends_candidate as candidate
import build_v073_pm23_recall_candidate as prior

RUN="20261029T235500Z"
POST="01234567-89ab-cdef-0123-456789abcdef"
AUTHOR="Thoughtful_Agent"


def fixture():
    db=sqlite3.connect(":memory:")
    db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,kind TEXT,details TEXT)")
    db.execute("CREATE TABLE decisions(run_id TEXT PRIMARY KEY,draft_sha256 TEXT,status TEXT,decided_at TEXT)")
    db.execute("INSERT INTO decisions VALUES('preserved','sha','approved','before')")
    return db


def values(**overrides):
    fields=dict(display_name="Thoughtful AI",relationship="interesting",
                interests="Distributed agents, local memory",notes="Enjoys thoughtful debate.")
    fields.update(overrides)
    return fields


def source_files(folder,author=AUTHOR):
    feed={"posts":[dict(id=POST,title="Memory and agents",
                        content="What do agents remember?",author=author)]}
    raw=json.dumps(feed).encode()
    (folder/("scout-feed-"+RUN+".json")).write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest()
    draft="What are the effects of persistent memory on collaborative agents?"
    rec=dict(schema=2,run_id=RUN,snapshot_file="scout-feed-"+RUN+".json",
             snapshot_sha256=digest,chosen_post_id=POST,
             chosen_title="Memory and agents",chosen_author=author,
             draft_comment=draft,
             draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),
             approval_sha256=hashlib.sha256((POST+"\n"+draft+"\n"+digest).encode()).hexdigest(),
             status="pending")
    (folder/("scout-result-"+RUN+".json")).write_text(json.dumps(rec))
    return rec


class FM1Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.patch=patch.object(common,"DATA",self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.db=fixture()
        self.addCleanup(self.db.close)
        self.rec=source_files(self.root)
        self.assertEqual(common.load_record(RUN)["run_id"],RUN)

    def get(self,ident):
        return friends._get(self.db,ident)

    def test_manual_lifecycle_revisions_stale_edit_and_archive_mute(self):
        friends.initialize(self.db)
        friends.initialize(self.db)
        fid=friends.create(self.db,"Agent_One",values())
        item=self.get(fid)
        self.assertEqual(item["handle"],"Agent_One")
        self.assertEqual(item["handle_key"],"agent_one")
        self.assertEqual(item["source_kind"],"manual")
        self.assertEqual(item["state"],"active")
        self.assertEqual(item["version"],1)
        friends.change(self.db,fid,item["sha256"],"edit",
                       values(relationship="friend",
                              notes="More conversations now."),
                       "Shared several useful public discussions")
        changed=self.get(fid)
        self.assertEqual(changed["version"],2)
        self.assertEqual(changed["relationship"],"friend")
        with self.assertRaisesRegex(ValueError,"modified"):
            friends.change(self.db,fid,item["sha256"],"archive")
        friends.change(self.db,fid,changed["sha256"],"mute")
        self.assertEqual(self.get(fid)["state"],"muted")
        with self.assertRaisesRegex(ValueError,"reactivated"):
            friends.change(self.db,fid,self.get(fid)["sha256"],"edit",values(),"try")
        friends.change(self.db,fid,self.get(fid)["sha256"],"reactivate")
        friends.change(self.db,fid,self.get(fid)["sha256"],"archive")
        self.assertEqual(self.get(fid)["state"],"archived")
        friends.change(self.db,fid,self.get(fid)["sha256"],"reactivate")
        self.assertEqual(self.get(fid)["version"],6)
        history=self.db.execute("SELECT version,action,snapshot_json FROM bob_friend_revisions "
                                "WHERE friend_id=? ORDER BY version",(fid,)).fetchall()
        self.assertEqual([r[1] for r in history],
                         ["create","edit","mute","reactivate","archive","reactivate"])
        self.assertIn("More conversations",history[1][2])
        self.assertEqual(self.db.execute("SELECT status FROM decisions").fetchone()[0],"approved")
        self.assertEqual(self.db.execute("SELECT count(*) FROM publish_settings").fetchone()[0],0)

    def test_duplicate_casefold_and_invalid_handles_refused(self):
        friends.create(self.db,"Agent_One",values())
        with self.assertRaisesRegex(ValueError,"already"):
            friends.create(self.db,"agent_one",values())
        for handle in ("x","", "../admin","@other","x"*41,"a b","a/b","🦄"):
            with self.subTest(handle=handle),self.assertRaisesRegex(ValueError,"handle"):
                friends.create(self.db,handle,values())
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friends").fetchone()[0],1)

    def test_scout_snapshot_author_verified_not_live_friendship(self):
        fid=friends.dispatch(self.db,dict(csrf="test",operation="scout_add",run_id=RUN))
        item=self.get(fid)
        self.assertEqual(item["handle"],AUTHOR)
        self.assertEqual(item["source_kind"],"scout_snapshot")
        self.assertEqual(item["source_run"],RUN)
        self.assertEqual(item["source_post"],POST)
        self.assertEqual(item["relationship"],"interesting")
        self.assertEqual(item["interests"],"")
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friends").fetchone()[0],1)
        with self.assertRaises(ValueError):
            friends.dispatch(self.db,dict(csrf="test",operation="scout_add",run_id=RUN))
        self.assertEqual(self.db.execute("SELECT status FROM decisions").fetchone()[0],"approved")

    def test_modified_scout_feed_or_fabricated_author_rejected(self):
        path=self.root/("scout-feed-"+RUN+".json")
        path.write_text('{"posts":[]}')
        with self.assertRaises(ValueError):
            friends.dispatch(self.db,dict(csrf="test",operation="scout_add",run_id=RUN))
        # Invalid input does not create a table or change existing decisions.
        self.assertIsNone(self.db.execute("SELECT name FROM sqlite_master WHERE name='bob_friends'").fetchone())
        source_files(self.root)
        f=self.root/("scout-result-"+RUN+".json")
        rec=json.loads(f.read_text())
        rec["chosen_author"]="ForgedOther"
        f.write_text(json.dumps(rec))
        with self.assertRaisesRegex(ValueError,"Source Scout run"):
            friends.dispatch(self.db,dict(csrf="test",operation="scout_add",run_id=RUN))
        self.assertIsNone(self.db.execute("SELECT name FROM sqlite_master WHERE name='bob_friends'").fetchone())
        source_files(self.root,author="unknown")
        # "unknown" is a placeholder, not a verified agent identity.
        with self.assertRaisesRegex(ValueError,"Scout author"):
            friends.dispatch(self.db,dict(csrf="test",operation="scout_add",run_id=RUN))

    def test_dispatch_exact_fields_and_noop_and_corruption(self):
        payload=dict(csrf="test",operation="create",handle="Agent_Two",**values())
        fid=friends.dispatch(self.db,payload)
        with self.assertRaisesRegex(ValueError,"Invalid friend form"):
            friends.dispatch(self.db,{**payload,"secret":"unexpected"})
        with self.assertRaisesRegex(ValueError,"No changes"):
            friends.dispatch(self.db,dict(csrf="test",operation="edit",id=fid,
                expected_sha=self.get(fid)["sha256"],reason="Nothing",**values()))
        with self.assertRaisesRegex(ValueError,"Reason"):
            friends.dispatch(self.db,dict(csrf="test",operation="edit",id=fid,
                expected_sha=self.get(fid)["sha256"],reason="",**values(
                    interests="Something different")))
        self.db.execute("UPDATE bob_friends SET notes='tampered' WHERE id=?",(fid,))
        with self.assertRaisesRegex(ValueError,"integrity"):
            friends._get(self.db,fid)
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friend_revisions").fetchone()[0],1)
        self.assertNotIn("tampered",friends.safe_error(sqlite3.OperationalError("db secrets")))

    def test_html_escapes_untrusted_notes_and_uses_manual_post_only(self):
        fid=friends.create(self.db,"ChatAgent",values(
            interests="<script>alert(1)</script>",
            notes="<img src=x onerror=alert(1)>"))
        page=friends.page(self.db,"token",lambda title,body,path:body,
                          {"edit":[fid]},[self.rec])
        self.assertNotIn("<script>alert(1)</script>",page)
        self.assertNotIn("<img src=x onerror=alert(1)>",page)
        self.assertIn("&lt;script&gt;",page)
        self.assertIn("Moltbook · Friends",page) if "Moltbook · Friends" in page else self.assertIn("Friends Manager",page)
        self.assertIn("PRIVATE",page.upper())
        self.assertIn("Thoughtful_Agent",page)
        self.assertIn('name="run_id"',page)
        self.assertIn('name="expected_sha"',page)
        self.assertIn('name="reason"',page)
        self.assertNotIn("follow/unfollow",page)
        self.assertNotIn('href="https://',page)

    def test_filters_and_muted_archive_visibility(self):
        first=friends.create(self.db,"Alpha_AI",values())
        second=friends.create(self.db,"Beta_AI",values())
        friends.change(self.db,second,self.get(second)["sha256"],"archive")
        active=friends.page(self.db,"token",lambda t,b,p:b,{"show":["active"]},[])
        self.assertIn("Alpha_AI",active)
        self.assertNotIn("Beta_AI",active)
        archived=friends.page(self.db,"token",lambda t,b,p:b,{"show":["archived"]},[])
        self.assertIn("Beta_AI",archived)
        self.assertIn("Reactivate",archived)
        hidden=friends.page(self.db,"token",lambda t,b,p:b,{"edit":[second]},[])
        self.assertIn("Reactivate this entry",hidden)
        self.assertNotIn('name="expected_sha" value="'+self.get(second)["sha256"]+'"><p>',hidden)
        search=friends.page(self.db,"token",lambda t,b,p:b,
                            {"show":["all"],"q":["distributed"]},[])
        self.assertIn("Alpha_AI",search)
        self.assertIn("Beta_AI",search)
        self.assertEqual(self.get(first)["state"],"active")

    def test_builder_preserves_old_post_auth_safety_and_navigation(self):
        old,navold=prior.build()
        new,nav=candidate.build()
        self.assertIn(b'urlsplit(self.path).path == "/moltbook/friends"',new)
        self.assertIn(b'if path == "/moltbook/friends":',new)
        self.assertIn(b'def _save_friend(self):',new)
        self.assertIn(b'self._valid_origin()',new)
        self.assertIn(b'hmac.compare_digest(values.get("csrf"',new)
        self.assertIn(b'max_num_fields=11',new)
        self.assertIn(b'/moltbook/friends',nav)
        self.assertNotIn(b'/moltbook/friends',navold)
        def methods(raw):
            tree=ast.parse(raw)
            cls=next(c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=="Handler")
            return {f.name:ast.dump(f,include_attributes=False) for f in cls.body
                    if isinstance(f,ast.FunctionDef)}
        a,b=methods(old),methods(new)
        self.assertEqual(set(b)-set(a),{"_save_friend"})
        for name in ("_save_memory","_save_memory_suggestion","_save_ai_memory",
                     "_save_recall","_apply_personality","_save_personality",
                     "_handle_publication","_handle_original","_handle_manage_bulk",
                     "_authenticated","_valid_origin","_change_activity_limits"):
            self.assertEqual(a[name],b[name],name)
        compile(new,"bob-activity-manager","exec")
        compile(nav,"navigation_shell.py","exec")


if __name__=="__main__":
    unittest.main()
