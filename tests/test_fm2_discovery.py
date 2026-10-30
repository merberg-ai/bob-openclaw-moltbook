"""FM2 offline profile and friend candidate review tests. No live network or agent."""
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
for root in ("src/lib/bob","webui","scripts"):
    sys.path.insert(0,str(ROOT/root))
import bob_publish_common as common
import bob_friends as friends
import bob_friend_discovery as discovery
import build_v074_fm2_discovery_candidate as builder
import build_v074_fm1_friends_candidate as previous

RID="20261029T235800Z"
PID="01234567-89ab-cdef-0123-456789abcdef"
AID="abcdef12-3456-7890-abcd-0123456789ab"
AUTHOR="MemoryBotOne"


def fixture(folder):
    feed=dict(posts=[dict(id=PID,title="A discussion of memory",
        author=AUTHOR,content="Agents could revisit past discussions.")])
    raw=json.dumps(feed).encode()
    (folder/("scout-feed-"+RID+".json")).write_bytes(raw)
    snap=hashlib.sha256(raw).hexdigest()
    draft="Could you elaborate on context windows and what should be remembered?"
    record=dict(schema=2,run_id=RID,status="pending",snapshot_sha256=snap,
        snapshot_file="scout-feed-"+RID+".json",draft_comment=draft,
        chosen_post_id=PID,chosen_title="A discussion of memory",chosen_author=AUTHOR,
        why="I find persistent agent memory and reliable reasoning interesting.",
        draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),
        approval_sha256=hashlib.sha256((PID+"\n"+draft+"\n"+snap).encode()).hexdigest())
    (folder/("scout-result-"+RID+".json")).write_text(json.dumps(record))
    return record


def db():
    con=sqlite3.connect(":memory:")
    con.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
    con.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,kind TEXT,details TEXT)")
    con.execute("CREATE TABLE decisions(run_id TEXT PRIMARY KEY,draft_sha256 TEXT,status TEXT,decided_at TEXT)")
    con.execute("INSERT INTO decisions VALUES('untouched','ok','approved','2026')")
    return con


def response(name=AUTHOR,code=200,extra=None):
    data={"success":True,"agent":dict(id=AID,name=name,description=
        "Interested in local reasoning, agent memory and collaboration.",
        karma=25,follower_count=7,following_count=2,is_claimed=True)}
    if extra:
        data.update(extra)
    return code,json.dumps(data).encode()


class MockHTTP:
    seen=[]
    reply=response()
    def __init__(self,host,timeout):
        self.seen.append(("CONNECT",host,timeout))
    def request(self,method,path,headers=None):
        self.seen.append((method,path,headers))
    def getresponse(self):
        status,body=self.reply
        class Result:
            def __init__(self,status,body):
                self.status=status
                self.raw=body
            def read(self,n):
                return self.raw[:n]
        return Result(status,body)
    def close(self):
        self.seen.append(("CLOSE",))


def vals(**kwargs):
    d=dict(display_name="Memory Bot",relationship="interesting",
           interests="Local AI memory and agent collaboration",
           notes="Owner reviewed the public profile")
    d.update(kwargs)
    return d


class FM2Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.rec=fixture(self.root)
        self.patch=patch.object(common,"DATA",self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.db=db()
        self.addCleanup(self.db.close)
        MockHTTP.seen=[]
        MockHTTP.reply=response()
        self.assertEqual(common.load_record(RID)["run_id"],RID)

    def store(self,handle=AUTHOR):
        p=discovery.profile_lookup(handle,connection_cls=MockHTTP)
        discovery.cache_profile(self.db,p)
        return p

    def suggestion(self):
        discovery.stage(self.db,RID)
        row=self.db.execute("SELECT "+",".join(discovery.PROPOSAL_COLS)+
                            " FROM bob_friend_candidates WHERE run_id=?",(RID,)).fetchone()
        return dict(zip(discovery.PROPOSAL_COLS,row))

    def test_fixed_https_get_no_auth_or_user_controlled_destination(self):
        profile=self.store()
        self.assertEqual(profile["handle"],AUTHOR)
        self.assertEqual(profile["agent_id"],AID)
        self.assertEqual(profile["followers"],7)
        self.assertEqual(profile["claimed"],1)
        self.assertTrue(discovery.fresh(discovery.cached(self.db,AUTHOR)))
        self.assertEqual(MockHTTP.seen[0],("CONNECT","www.moltbook.com",8))
        self.assertEqual(MockHTTP.seen[1][0],"GET")
        self.assertEqual(MockHTTP.seen[1][1],
                         "/api/v1/agents/profile?name=MemoryBotOne")
        self.assertNotIn("Authorization",MockHTTP.seen[1][2])
        self.assertEqual(MockHTTP.seen[-1],("CLOSE",))
        self.assertEqual(self.db.execute("SELECT status FROM decisions").fetchone()[0],"approved")

    def test_get_errors_wrong_identity_and_secret_never_leaked(self):
        for status,msg in ((404,"not found"),(401,"authorization"),(403,"authorization"),
                           (429,"rate limiting"),(500,"temporarily")):
            MockHTTP.reply=response(code=status)
            with self.subTest(status=status),self.assertRaisesRegex(ValueError,msg):
                discovery.profile_lookup(AUTHOR,connection_cls=MockHTTP)
        MockHTTP.reply=response(name="Impersonator")
        with self.assertRaisesRegex(ValueError,"different"):
            discovery.profile_lookup(AUTHOR,connection_cls=MockHTTP)
        MockHTTP.reply=response(extra={"success":False})
        with self.assertRaisesRegex(ValueError,"unexpected"):
            discovery.profile_lookup(AUTHOR,connection_cls=MockHTTP)
        MockHTTP.reply=(200,b'{"api_key":"SECRET","agent":{}}')
        with self.assertRaisesRegex(ValueError,"unexpected"):
            discovery.profile_lookup(AUTHOR,connection_cls=MockHTTP)
        self.assertNotIn("SECRET",discovery.safe_error(ValueError("SECRET")))
        with self.assertRaises(ValueError):
            discovery.profile_lookup("../bad",connection_cls=MockHTTP)
        self.assertEqual(discovery.safe_error(sqlite3.OperationalError("PRIVATE DATA")),
                         "Friend discovery unchanged. Reload and check the selected profile.")

    def test_source_linked_suggestions_need_owner_stage_and_reverify(self):
        self.assertEqual(discovery.source(RID)[0],AUTHOR)
        item=self.suggestion()
        self.assertEqual(item["status"],"pending")
        self.assertIn("persistent agent memory",item["why"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friends").fetchone()[0],0)
        with self.assertRaisesRegex(ValueError,"already staged"):
            discovery.stage(self.db,RID)
        path=self.root/("scout-feed-"+RID+".json")
        path.write_text('{"posts":[]}')
        with self.assertRaisesRegex(ValueError,"Source Scout run"):
            discovery.review(self.db,item["id"],item["sha256"],"approve","thoughtful",vals())
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friends").fetchone()[0],0)

    def test_approval_requires_recent_profile_and_creates_one_private_friend(self):
        row=self.suggestion()
        with self.assertRaisesRegex(ValueError,"Look up a fresh"):
            discovery.review(self.db,row["id"],row["sha256"],"approve","reviewed",vals())
        self.store()
        fid=discovery.review(self.db,row["id"],row["sha256"],"approve",
                             "Verified public description and topics",vals())
        friend=friends._get(self.db,fid)
        self.assertEqual(friend["handle"],AUTHOR)
        self.assertEqual(friend["relationship"],"interesting")
        self.assertEqual(friend["source_run"],RID)
        self.assertEqual(friend["source_post"],PID)
        self.assertEqual(friend["source_kind"],"scout_snapshot")
        self.assertEqual(friend["interests"],vals()["interests"])
        self.assertEqual(self.db.execute("SELECT status FROM decisions").fetchone()[0],"approved")
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friend_candidates WHERE status='approved'").fetchone()[0],1)
        with self.assertRaises(ValueError):
            discovery.review(self.db,row["id"],row["sha256"],"approve","again",vals())
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friends").fetchone()[0],1)

    def test_reject_without_profile_and_invalid_form_never_adds(self):
        item=self.suggestion()
        with self.assertRaisesRegex(ValueError,"Invalid discovery"):
            discovery.dispatch(self.db,dict(csrf="csrf",operation="approve",id=item["id"],
                expected_sha=item["sha256"],reason="test",**vals(),api_key="forged"))
        with self.assertRaisesRegex(ValueError,"candidate changed"):
            discovery.review(self.db,item["id"],"0"*64,"reject","uninteresting")
        discovery.review(self.db,item["id"],item["sha256"],"reject","Not interesting")
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friends").fetchone()[0],0)
        with self.assertRaisesRegex(ValueError,"already reviewed"):
            discovery.review(self.db,item["id"],item["sha256"],"reject","again")

    def test_cached_profile_integrity_staleness_and_identity_collision(self):
        p=self.store()
        self.assertTrue(discovery.fresh(discovery.cached(self.db,AUTHOR)))
        self.db.execute("UPDATE bob_friend_profile_cache SET description='TAMPERED' "
                        "WHERE handle_key=?",(AUTHOR.casefold(),))
        self.assertIsNone(discovery.cached(self.db,AUTHOR))
        # Reset an authentic cache, then replay a different Moltbook agent ID.
        self.db.execute("DELETE FROM bob_friend_profile_cache")
        self.store()
        second=dict(p,agent_id=PID)
        second["sha256"]=discovery.seal(second,discovery.PROFILE_COLS)
        with self.assertRaisesRegex(ValueError,"different agent"):
            discovery.cache_profile(self.db,second)
        self.db.execute("UPDATE bob_friend_profile_cache SET fetched_at='2020-01-01T00:00:00+00:00'")
        self.assertFalse(discovery.fresh(discovery.cached(self.db,AUTHOR)))

    def test_html_escaping_and_audited_review_controls(self):
        row=self.suggestion()
        self.store()
        html=discovery.page(self.db,"csrf",lambda title,body,path:body,
            {"profile":[AUTHOR]},[self.rec])
        self.assertIn("Look up public profile",html)
        self.assertIn("Review pending candidates",html)
        self.assertIn("Approve and add to Friends",html)
        self.assertIn("Reject suggestion",html)
        self.assertIn("API-reported profile",html)
        self.assertIn("No new verified Scout candidates",html)
        self.assertNotIn('name="api_key"',html)
        self.assertNotIn("follow this user",html)
        # Stored remote description must be escaped.
        self.db.execute("DELETE FROM bob_friend_profile_cache")
        MockHTTP.reply=response(extra={"agent":dict(id=AID,name=AUTHOR,
            description="<img src=x onerror=alert(1)>",karma=0)})
        self.store()
        html=discovery.page(self.db,"csrf",lambda t,b,p:b,{"profile":[AUTHOR]},[])
        self.assertIn("&lt;img",html)
        self.assertNotIn("<img src=x",html)
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_friends").fetchone()[0],0)

    def test_generated_manager_route_isolated_from_older_handlers(self):
        old,oldnav=previous.build()
        new,nav=builder.build()
        self.assertIn(b'urlsplit(self.path).path == "/moltbook/discover"',new)
        self.assertIn(b'if path == "/moltbook/discover":',new)
        self.assertIn(b'def _save_discovery(self):',new)
        self.assertIn(b'self._valid_origin()',new)
        self.assertIn(b'hmac.compare_digest(values.get("csrf"',new)
        self.assertIn(b'from urllib.parse import quote',new)
        self.assertIn(b'max_num_fields=12',new)
        self.assertIn(b'/moltbook/discover',nav)
        self.assertNotIn(b'/moltbook/discover',oldnav)
        def members(raw):
            tree=ast.parse(raw)
            cls=next(c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=="Handler")
            return {f.name:ast.dump(f,include_attributes=False)
                    for f in cls.body if isinstance(f,ast.FunctionDef)}
        before,after=members(old),members(new)
        self.assertEqual(set(after)-set(before),{"_save_discovery"})
        for name in ("_save_friend","_save_memory","_save_memory_suggestion",
                     "_save_ai_memory","_save_recall","_apply_personality",
                     "_save_personality","_handle_publication","_handle_original",
                     "_handle_manage_bulk","_authenticated","_valid_origin"):
            self.assertEqual(before[name],after[name],name)
        compile(new,"generated-manager","exec")
        compile(nav,"generated-nav","exec")


if __name__=="__main__":
    unittest.main()
