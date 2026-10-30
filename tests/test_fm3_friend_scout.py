"""FM3 offline safety acceptance: synthetic friends, API responses, Scout and queue."""
from __future__ import annotations
import ast
from datetime import datetime,timezone,date,timedelta
import hashlib
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader,module_from_spec
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for path in ("src/lib/bob","webui","scripts","src/bin"):
    sys.path.insert(0,str(ROOT/path))

import bob_publish_common as common
import bob_friends as friends
import bob_friend_scout as fs
import build_v074_fm2_discovery_candidate as prior
import build_v074_fm3_friend_scout_candidate as builder

AID="abcdef12-3456-7890-abcd-0123456789ab"
BID="fedcba12-3456-7890-abcd-0123456789ab"
PIDA="01234567-89ab-cdef-0123-456789abcdef"
PIDB="01234567-89ab-cdef-0123-456789abcdea"


def vals(relationship="friend"):
    return dict(display_name="Friend label",relationship=relationship,
                interests="local memory, astronomy",notes="Private, not for publication")


def make_db(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                   "at TEXT NOT NULL,kind TEXT NOT NULL,details TEXT NOT NULL)")
        db.execute("CREATE TABLE decisions(run_id TEXT PRIMARY KEY,draft_sha256 TEXT,"
                   "status TEXT,decided_at TEXT)")
        db.execute("CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,approval_sha256 TEXT,"
                   "post_id TEXT,draft_comment TEXT,mode TEXT,state TEXT,created_at TEXT,updated_at TEXT)")
        friends.create(db,"AgentAlpha",vals())
        friends.create(db,"AgentBeta",vals("interesting"))
        friends.create(db,"AgentGamma",vals("acquaintance"))


def feed_post(i):
    return {"id":f"10000000-0000-4000-8000-{i:012d}","title":"Global discussion",
            "content":"Some global observation","author":"Other"}


def getter_fixture():
    paths=[]
    def getter(path):
        paths.append(path)
        if path.startswith("/api/v1/agents/profile?"):
            name=path.split("name=")[-1]
            ident=AID if name=="AgentAlpha" else BID
            pid=PIDA if name=="AgentAlpha" else PIDB
            return {"success":True,"agent":{"name":name,"id":ident},
                    "recentPosts":[{"id":pid,"title":"interesting"}]}
        if path=="/api/v1/posts/"+PIDA:
            return {"success":True,"post":{"id":PIDA,"title":"Shared AI memory",
                    "content":"A thoughtful question about memory and autonomy.",
                    "author":{"name":"AgentAlpha","id":AID}}}
        if path=="/api/v1/posts/"+PIDB:
            return {"success":True,"post":{"id":PIDB,"title":"Learning through friendship",
                    "content":"What could agents learn from one another?",
                    "author":{"name":"AgentBeta","id":BID}}}
        raise AssertionError("Unexpected external URL: "+path)
    return getter,paths


def create_record(folder,rid,*,friend_marker,flag,author_override=None):
    post={"id":PIDA if friend_marker else PIDB,"title":"Thoughtful memory thread",
          "content":"An interesting technical discussion",
          "author":author_override or ("AgentAlpha" if friend_marker else "Other")}
    if friend_marker:
        post["from_friend"]=True
    snapshot={"source":"synthetic","posts":[post]}
    if friend_marker:
        snapshot["friend_focus"]=True
    raw=json.dumps(snapshot).encode()
    (folder/("scout-feed-"+rid+".json")).write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest()
    draft="I find the idea compelling. What evidence would change your mind?"
    rec={"schema":2,"run_id":rid,"status":"pending",
         "chosen_post_id":post["id"],"chosen_title":post["title"],
         "chosen_author":post["author"],"draft_comment":draft,
         "draft_sha256":hashlib.sha256(draft.encode()).hexdigest(),
         "snapshot_sha256":digest,"snapshot_file":"scout-feed-"+rid+".json",
         "approval_sha256":hashlib.sha256(
             (post["id"]+"\n"+draft+"\n"+digest).encode()).hexdigest()}
    if flag:
        rec["friend_focus"]=True
    (folder/("scout-result-"+rid+".json")).write_text(json.dumps(rec))
    return rec


def script(path,name):
    loader=SourceFileLoader(name,str(ROOT/path))
    spec=spec_from_loader(loader.name,loader)
    mod=module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class FM3Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.dbpath=self.root/"activity-queue.sqlite3"
        make_db(self.dbpath)
        self.p1=patch.object(common,"DB",self.dbpath)
        self.p2=patch.object(common,"DATA",self.root)
        self.p1.start();self.p2.start()
        self.addCleanup(self.p1.stop);self.addCleanup(self.p2.stop)

    def db(self):
        return sqlite3.connect(self.dbpath)

    def enable(self):
        with self.db() as db:
            return fs.change(db,dict(csrf="token",enabled="1",expected="0",
                                     confirmation=fs.CONFIRM))

    def test_opt_in_off_does_not_call_network_or_change_feed(self):
        self.assertEqual(fs.selected_watch(),[])
        posts=[feed_post(i) for i in range(6)]
        def fail(_):
            raise AssertionError("No outbound request is permitted when off")
        actual,count=fs.enrich(posts,set(),getter=fail)
        self.assertEqual((actual,count),(posts,0))
        with self.db() as db:
            self.assertFalse(fs.enabled(db))
            self.assertEqual(db.execute(
                "SELECT count(*) FROM publish_jobs").fetchone()[0],0)

    def test_toggle_requires_exact_confirmation_and_stale_guard(self):
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"Confirmation"):
                fs.change(db,dict(csrf="x",enabled="1",expected="0",confirmation="yes"))
            with self.assertRaisesRegex(ValueError,"Invalid"):
                fs.change(db,dict(csrf="x",enabled="1",expected="0",
                                  confirmation=fs.CONFIRM,hijack="1"))
            fs.change(db,dict(csrf="x",enabled="1",expected="0",confirmation=fs.CONFIRM))
            self.assertTrue(fs.enabled(db))
            with self.assertRaisesRegex(ValueError,"changed"):
                fs.change(db,dict(csrf="x",enabled="1",expected="0",confirmation=fs.CONFIRM))
            fs.change(db,dict(csrf="x",enabled="0",expected="1",confirmation=""))
            self.assertFalse(fs.enabled(db))
            self.assertEqual(db.execute(
                "SELECT count(*) FROM publish_events WHERE kind='bob_friend_scout_setting'").fetchone()[0],2)

    def test_only_active_and_digest_valid_watchlist_and_fair_rotation(self):
        with self.db() as db:
            beta=db.execute("SELECT id,sha256 FROM bob_friends WHERE handle='AgentBeta'").fetchone()
            friends.change(db,beta[0],beta[1],"mute")
            gamma=db.execute("SELECT id FROM bob_friends WHERE handle='AgentGamma'").fetchone()[0]
            db.execute("UPDATE bob_friends SET interests='TAMPERED' WHERE id=?",(gamma,))
        self.enable()
        selected=fs.selected_watch(date=date(2026,10,29))
        self.assertEqual([x["handle"] for x in selected],["AgentAlpha"])
        with self.db() as db:
            beta=db.execute("SELECT id,sha256 FROM bob_friends WHERE handle='AgentBeta'").fetchone()
            friends.change(db,beta[0],beta[1],"reactivate")
        selected=fs.selected_watch(date=date(2026,10,29))
        self.assertEqual({x["handle"] for x in selected},{"AgentAlpha","AgentBeta"})
        self.assertNotIn("TAMPERED",json.dumps(selected))
        self.assertEqual(len(selected),2)

    def test_profile_and_post_only_from_matching_provider_identity(self):
        self.enable()
        watch=fs.selected_watch(date=date(2026,10,29))
        getter,paths=getter_fixture()
        result=fs.read_friend_posts(watch,set(),getter=getter)
        self.assertEqual(len(result),2)
        self.assertEqual({p["author"] for p in result},{"AgentAlpha","AgentBeta"})
        self.assertTrue(all(p.get("from_friend") is True for p in result))
        self.assertEqual(len(paths),4)
        self.assertEqual(sum(p.startswith("/api/v1/agents/profile?") for p in paths),2)
        self.assertEqual(sum(p.startswith("/api/v1/posts/") for p in paths),2)
        self.assertNotIn("Private",json.dumps(result))
        # Seen posts are never fetched even if the profile advertises them.
        getter2,paths2=getter_fixture()
        result=fs.read_friend_posts(watch,{PIDA,PIDB},getter=getter2)
        self.assertEqual(result,[])
        self.assertEqual(len(paths2),2)

    def test_enrichment_blends_four_global_and_two_friends(self):
        self.enable()
        baseline=[feed_post(i) for i in range(6)]
        getter,paths=getter_fixture()
        combined,n=fs.enrich(baseline,set(),getter=getter,date=date(2026,10,29))
        self.assertEqual(n,2)
        self.assertEqual(len(combined),6)
        self.assertEqual(combined[:4],baseline[:4])
        self.assertTrue(all(x["from_friend"] for x in combined[4:]))
        self.assertEqual(len(paths),4)

    def test_invalid_or_mismatched_profiles_and_posts_never_added(self):
        self.enable()
        agents=fs.selected_watch(date=date(2026,10,29))
        cases=[
            {"success":True,"agent":{"name":"Impostor","id":AID},"recentPosts":[{"id":PIDA}]},
            {"success":True,"agent":{"name":"AgentAlpha","id":"bad"},"recentPosts":[{"id":PIDA}]},
            {"success":True,"agent":{"name":"AgentAlpha","id":AID},"recentPosts":[{"id":"bad"}]},
            {"success":False,"agent":{"name":"AgentAlpha","id":AID},"recentPosts":[{"id":PIDA}]},
        ]
        for result in cases:
            with self.subTest(result=result):
                seen=[]
                def get(path):
                    seen.append(path)
                    return result
                self.assertEqual(fs.profile_posts(agents[0],getter=get),[])
                self.assertEqual(len(seen),1)
        def wrong_author(path):
            if "profile?" in path:
                return {"success":True,"agent":{"name":"AgentAlpha","id":AID},
                        "recentPosts":[{"id":PIDA}]}
            return {"success":True,"post":{"id":PIDA,"title":"Some text",
                    "content":"Untrusted text","author":{"name":"WrongAgent","id":AID}}}
        self.assertEqual(fs.read_friend_posts(agents[:1],set(),getter=wrong_author),[])
        def wrong_id(path):
            if "profile?" in path:
                return {"success":True,"agent":{"name":"AgentAlpha","id":AID},
                        "recentPosts":[{"id":PIDA}]}
            return {"success":True,"post":{"id":PIDA,"title":"Some text",
                    "content":"Untrusted text","author":{"name":"AgentAlpha","id":BID}}}
        self.assertEqual(fs.read_friend_posts(agents[:1],set(),getter=wrong_id),[])

    def test_http_adapter_fixed_host_get_no_api_keys_redirects_or_publishing(self):
        calls=[]
        class Response:
            status=200
            def read(self,n):
                return json.dumps({"success":True,"agent":{"id":AID,"name":"AgentAlpha"}}).encode()
        class FakeConn:
            def __init__(self,host,timeout):
                calls.append(("connection",host,timeout))
            def request(self,method,path,headers):
                calls.append(("request",method,path,headers))
            def getresponse(self):
                return Response()
            def close(self):
                calls.append(("close",))
        result=fs._json_get("/api/v1/agents/profile?name=AgentAlpha",connection_cls=FakeConn)
        self.assertIsNotNone(result)
        self.assertEqual(calls[0],("connection","www.moltbook.com",8))
        self.assertEqual(calls[1][1],"GET")
        self.assertTrue(calls[1][2].startswith("/api/v1/agents/profile?name="))
        self.assertNotIn("Authorization",calls[1][3])
        self.assertEqual(calls[-1],("close",))

    def test_auto_publisher_refuses_snapshot_friend_markers_even_if_flag_removed(self):
        t=datetime.now(timezone.utc).replace(microsecond=0)
        rid=t.strftime("%Y%m%dT%H%M%SZ")
        earlier=(t-timedelta(seconds=5)).isoformat()
        with self.db() as db:
            db.execute("INSERT INTO publish_settings VALUES('auto_enabled','1')")
            db.execute("INSERT INTO publish_settings VALUES('auto_since',?)",(earlier,))
        rec=create_record(self.root,rid,friend_marker=True,flag=False)
        self.assertIsNotNone(common.load_record(rid))
        with common.connect() as db:
            self.assertEqual(common.auto_candidates(db),0)
            self.assertEqual(db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0],0)
        # The identical public draft still remains eligible for deliberate
        # manual review and queue through legacy approval + queue_manual.
        with common.connect() as db:
            db.execute("INSERT INTO decisions VALUES(?,?,?,?)",
                       (rid,rec["approval_sha256"],"approved",common.now()))
            common.queue_manual(db,rid)
            self.assertEqual(db.execute("SELECT mode FROM publish_jobs WHERE run_id=?",
                                        (rid,)).fetchone()[0],"manual")

    def test_friend_author_found_in_global_feed_is_never_auto_queued(self):
        t=datetime.now(timezone.utc).replace(microsecond=0)
        rid=t.strftime("%Y%m%dT%H%M%SZ")
        earlier=(t-timedelta(seconds=5)).isoformat()
        with self.db() as db:
            db.execute("INSERT INTO publish_settings VALUES('auto_enabled','1')")
            db.execute("INSERT INTO publish_settings VALUES('auto_since',?)",(earlier,))
        # No marker whatsoever: same ordinary global feed source but the
        # chosen author belongs to FM1 Friends. Must still require manual.
        create_record(self.root,rid,friend_marker=False,flag=False,
                      author_override="AgentAlpha")
        with common.connect() as db:
            self.assertEqual(common.auto_candidates(db),0)
            self.assertEqual(db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0],0)

    def test_scan_attempts_have_explicit_safe_status_codes(self):
        baseline=[feed_post(i) for i in range(6)]
        status={}
        unchanged,count=fs.enrich(baseline,set(),diagnostics=status)
        self.assertEqual((unchanged,count),(baseline,0))
        self.assertEqual(status["state"],"no_eligible_active_friends")
        self.enable()
        status={}
        getter,_=getter_fixture()
        found,count=fs.enrich(baseline,set(),getter=getter,
                              date=date(2026,10,29),diagnostics=status)
        self.assertEqual(count,2)
        self.assertEqual(status["state"],"friend_posts_included")
        status={}
        no_posts,count=fs.enrich(baseline,set(),getter=lambda _: None,
                                 date=date(2026,10,29),diagnostics=status)
        self.assertEqual((no_posts,count),(baseline,0))
        self.assertEqual(status["state"],"no_verified_public_posts")

    def test_normal_global_post_can_still_enter_preexisting_auto_queue(self):
        t=datetime.now(timezone.utc).replace(microsecond=0)
        rid=t.strftime("%Y%m%dT%H%M%SZ")
        earlier=(t-timedelta(seconds=5)).isoformat()
        with self.db() as db:
            db.execute("INSERT INTO publish_settings VALUES('auto_enabled','1')")
            db.execute("INSERT INTO publish_settings VALUES('auto_since',?)",(earlier,))
        create_record(self.root,rid,friend_marker=False,flag=False)
        with common.connect() as db:
            self.assertEqual(common.auto_candidates(db),1)
            self.assertEqual(db.execute("SELECT mode FROM publish_jobs").fetchone()[0],"auto")

    def test_ui_honest_status_and_no_automatic_action(self):
        with self.db() as db:
            inactive=fs.page(db,"csrf",lambda title,body,path:body,[])
            self.assertIn("Status: Disabled",inactive)
            self.assertIn(fs.CONFIRM,inactive)
            self.assertIn("never eligible for automatic",inactive)
            self.assertIn("AgentAlpha",inactive)
            self.assertNotIn("Auto follow",inactive)
        self.enable()
        with self.db() as db:
            enabled=fs.page(db,"csrf",lambda title,body,path:body,[])
            self.assertIn("Status: Enabled",enabled)
            self.assertIn("Disable friend scouting",enabled)
            self.assertNotIn("Private, not for publication",enabled)

    def test_scout_prompt_unchanged_review_and_no_tools_rules(self):
        scout=script("src/bin/bob-moltbook-scout","scout_fm3_synthetic")
        snap={"posts":[dict(id=PIDA,title="Memory question",content="A note",
                             author="AgentAlpha",from_friend=True)]}
        original=scout.scout_prompt(snap)
        updated=scout.scout_prompt(snap,friend_hint=True)
        self.assertIn("Do not use ANY tools",updated)
        self.assertIn("human review only",updated)
        self.assertIn("genuinely",updated)
        self.assertNotEqual(original,updated)
        self.assertIn("BEGIN_UNTRUSTED_MOLTBOOK_JSON",updated)
        self.assertIn("DRAFT_COMMENT_START",updated)
        self.assertIn("DRAFT_COMMENT_END",updated)
        self.assertIn("from_friend",updated)

    def test_builder_maintains_old_handler_auth_and_queue_routes(self):
        old,nav_before=prior.build()
        new,nav_after=builder.build()
        self.assertIn(b'if path == "/moltbook/friend-scout":',new)
        self.assertIn(b'def _save_friend_scout(self):',new)
        self.assertIn(b'self._valid_origin()',new)
        self.assertIn(b'hmac.compare_digest(values.get("csrf"',new)
        self.assertIn(b'/moltbook/friend-scout',nav_after)
        self.assertNotIn(b'/moltbook/friend-scout',nav_before)
        def funcs(raw):
            tree=ast.parse(raw)
            cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="Handler")
            return {m.name:ast.dump(m,include_attributes=False) for m in cls.body
                    if isinstance(m,ast.FunctionDef)}
        before,after=funcs(old),funcs(new)
        self.assertEqual(set(after)-set(before),{"_save_friend_scout"})
        for name in ("_authenticated","_valid_origin","_save_discovery","_save_friend",
                     "_save_recall","_save_memory","_handle_publication",
                     "_handle_original","_handle_manage_bulk"):
            self.assertEqual(before[name],after[name],name)
        compile(new,"generated-manager","exec")
        compile(nav_after,"generated-nav","exec")


if __name__=="__main__":
    unittest.main()
