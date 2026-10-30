"""FM4.1 private Social Memory tests: source integrity, scope and host auth.

All records are synthetic and local. No Moltbook, Ollama or OpenClaw calls.
No files on the live OMEN and no API publication are touched.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
import ast
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
for folder in ("src/lib/bob","scripts","webui"):
    sys.path.insert(0,str(ROOT/folder))
import bob_publish_common as common
import bob_friends as friends
import bob_friend_scout as scout
import bob_social_memory as social
import build_v076_oc4_candidate as prior
import build_v076_fm41_candidate as candidate

RUN="20261030T120000Z"
PID="11111111-2222-3333-4444-555555555555"
CID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
AID="01234567-89ab-cdef-0123-456789abcdef"
PRIVATE="PRIVATE-FRIEND-OPERATOR-NOTES-NEVER-LEAK"
MALICIOUS="<img src=x onerror=alert(1)>"

class SocialTimelineTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for key,value in (("DATA",self.root),
                          ("DB",self.root/"activity.sqlite3")):
            p=patch.object(common,key,value)
            p.start()
            self.addCleanup(p.stop)
        with common.connect() as db:
            self.friend_id=friends.create(db,"BobBuddy",{
              "display_name":"Buddy","relationship":"interesting",
              "interests":"INTERESTS-"+PRIVATE,"notes":PRIVATE})
            self.other=friends.create(db,"DifferentAgent",{
              "display_name":"Different","relationship":"acquaintance",
              "interests":"", "notes":"another private note"})
            scout.init_interests(db)
            scout.init_interest_ai(db)
            scout.focus_init(db)
        self.make_record()
        self.make_history()

    def make_record(self):
        feed={"posts":[{"id":PID,"title":MALICIOUS,
                        "content":"Public discussion about AI memory",
                        "author":"BobBuddy"}]}
        raw=json.dumps(feed).encode()
        (self.root/("scout-feed-"+RUN+".json")).write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest()
        draft="What helps an agent revise its beliefs over time?"
        approval=hashlib.sha256((PID+"\n"+draft+"\n"+digest).encode()).hexdigest()
        record={"schema":2,"run_id":RUN,"status":"pending","chosen_post_id":PID,
                "chosen_title":MALICIOUS,"chosen_author":"BobBuddy",
                "draft_comment":draft,
                "draft_sha256":hashlib.sha256(draft.encode()).hexdigest(),
                "snapshot_sha256":digest,"snapshot_file":"scout-feed-"+RUN+".json",
                "approval_sha256":approval,
                "why":"I wonder whether agents can learn from past mistakes."}
        (self.root/("scout-result-"+RUN+".json")).write_text(json.dumps(record))
        self.record=record
        self.assertIsNotNone(common.load_record(RUN))

    def make_history(self):
        now="2026-10-30T12:10:00+00:00"
        with common.connect() as db:
            item=dict(id="f"*24,friend_id=self.friend_id,run_id=RUN,
                      post_id=PID,handle="BobBuddy",
                      idea=self.record["why"][:320],
                      status="approved",created_at=now,updated_at=now,
                      review_reason="owner reviewed",version=2)
            item["sha256"]=scout.interest_seal(item)
            db.execute("INSERT INTO bob_friend_interest_proposals("+
                       ",".join(scout.INTEREST_COLS)+") VALUES("+
                       ",".join("?" for _ in scout.INTEREST_COLS)+")",
                       [item[k] for k in scout.INTEREST_COLS])
            ai=dict(id="a"*24,job_id="b"*24,friend_id=self.friend_id,
                    run_id=RUN,post_id=PID,
                    snapshot_sha=self.record["snapshot_sha256"],
                    handle="BobBuddy",idea="Maybe AI social memory matters.",
                    reason="Local reasoning",uncertainty="This is only an idea.",
                    confidence="low",status="pending",
                    created_at=now,updated_at=now,review_reason="",version=1)
            ai["sha256"]=scout.ai_seal(ai)
            db.execute("INSERT INTO bob_friend_ai_proposals("+
                       ",".join(scout.AI_PROP_COLS)+") VALUES("+
                       ",".join("?" for _ in scout.AI_PROP_COLS)+")",
                       [ai[k] for k in scout.AI_PROP_COLS])
            focus=dict(id="c"*24,friend_id=self.friend_id,
                friend_sha=friends._get(db,self.friend_id)["sha256"],
                watch_sha="default",handle="BobBuddy",status="completed",
                created_at=now,updated_at=now,error_code="",
                result_json=json.dumps({"handle":"BobBuddy","agent_id":AID,
                                        "posts":[{"id":PID,"title":MALICIOUS}]}),
                idea_json=json.dumps({"interest":"Potential shared interest."}),
                review_status="approved",review_reason="owner reviewed",version=2)
            focus["sha256"]=scout.focus_seal(focus)
            db.execute("INSERT INTO bob_friend_focus_jobs("+
                       ",".join(scout.FOCUS_COLS)+") VALUES("+
                       ",".join("?" for _ in scout.FOCUS_COLS)+")",
                       [focus[k] for k in scout.FOCUS_COLS])
            db.execute("INSERT INTO publish_jobs(run_id,approval_sha256,"
                       "post_id,draft_comment,mode,state,created_at,updated_at,"
                       "attempted_at,comment_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (RUN,self.record["approval_sha256"],PID,
                        self.record["draft_comment"],"manual","published",
                        now,now,now,CID))

    def get(self,**kwargs):
        return social.snapshot(path=self.root/"activity.sqlite3",params=kwargs)

    def test_private_timeline_with_verified_multiple_source_types(self):
        d=self.get()
        self.assertTrue(d["available"])
        self.assertEqual(d["total"],2)
        self.assertEqual(d["selected"]["handle"],"BobBuddy")
        events=d["entries"]
        kinds={x["kind"] for x in events}
        self.assertTrue({"operator","observed","review","interpretation","focus","publication"}<=kinds)
        self.assertTrue(any(x["title"]=="Comment API-acknowledged" for x in events))
        self.assertTrue(any(x["title"]=="Selected a public discussion" for x in events))
        self.assertTrue(any(x["title"]=="Owner-reviewed saved Scout interest" for x in events))
        self.assertTrue(any(x["title"]=="Public-focus reaction · approved" for x in events))
        exported=json.dumps(d)
        self.assertNotIn(PRIVATE,exported)
        self.assertNotIn("another private note",exported)
        self.assertNotIn(self.record["draft_comment"],exported)
        self.assertNotIn("apikey",exported.lower())
        self.assertNotIn("followed on Moltbook",exported)
        self.assertTrue(all(x["trust"] in ("operator","observed","interpretation","review")
                            for x in events))
        self.assertLessEqual(len(events),social.MAX_EVENTS)

    def test_tampered_feed_removes_selected_and_hides_proposal_text(self):
        (self.root/("scout-feed-"+RUN+".json")).write_text('{"posts":[]}')
        events=self.get()["entries"]
        self.assertFalse(any(x["kind"]=="observed" for x in events))
        self.assertFalse(any(x["kind"]=="publication" for x in events))
        self.assertFalse(any(x["detail"]==self.record["why"] for x in events))
        self.assertFalse(any("Maybe AI social memory matters" in x["detail"] for x in events))
        self.assertTrue(any(x["status"]=="missing" for x in events))

    def test_tampered_proposal_digest_not_displayed(self):
        with common.connect() as db:
            db.execute("UPDATE bob_friend_ai_proposals SET idea=?",
                       (PRIVATE,))
        events=self.get()["entries"]
        self.assertNotIn(PRIVATE,json.dumps(events))
        self.assertFalse(any(x["title"].startswith("Local model proposal") for x in events))

    def test_tampered_friend_record_is_suppressed(self):
        with common.connect() as db:
            db.execute("UPDATE bob_friends SET handle='Changed' WHERE id=?",
                       (self.friend_id,))
        d=self.get()
        self.assertNotIn(self.friend_id,[x["id"] for x in d["people"]])
        self.assertNotIn(PRIVATE,json.dumps(d))

    def test_search_filter_and_other_agent_never_inherits_history(self):
        d=self.get(q=["Different"])
        self.assertEqual(d["total"],1)
        self.assertEqual(d["selected"]["handle"],"DifferentAgent")
        self.assertEqual([x["kind"] for x in d["entries"]],["operator"])
        none=self.get(q=["NoNameExists"])
        self.assertEqual(none["total"],0)
        self.assertEqual(none["entries"],[])
        self.assertIsNone(none["selected"])
        invalid=self.get(page=["99999"],agent=[MALICIOUS])
        self.assertEqual(invalid["page"],1)

    def test_readonly_db_file_not_modified_and_missing_db_empty(self):
        dbfile=self.root/"activity.sqlite3"
        size_before=dbfile.stat().st_size
        _=self.get()
        self.assertEqual(size_before,dbfile.stat().st_size)
        missing=social.snapshot(path=self.root/"missing.sqlite")
        self.assertFalse(missing["available"])
        self.assertEqual(missing["entries"],[])

    def test_escape_untrusted_public_title_and_preserve_labels(self):
        d=self.get()
        html=social.page(lambda title,body,current:body,data=d)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;",html)
        self.assertNotIn("<img src=x onerror",html)
        self.assertIn("Social Memory · FM4.1",html)
        self.assertIn("Observed evidence",html)
        self.assertIn("Owner reviewed",html)
        self.assertIn("Tentative",html)
        self.assertIn("not proof of",html)
        self.assertNotIn(PRIVATE,html)
        self.assertNotIn('<form method="post"',html)
        self.assertIn("@media(max-width:750px)",social.STYLE)

    def test_manager_only_adds_authorized_get_and_navigation(self):
        old,oldnav=prior.build()
        new,nav=candidate.build()
        self.assertIn(b'elif urlsplit(self.path).path == "/moltbook/social-memory":',new)
        self.assertIn(b'max_num_fields=4',new)
        self.assertIn(b'("/moltbook/social-memory", "Moltbook',nav)
        self.assertNotIn(b'moltbook/social-memory',oldnav)
        def handler_methods(src):
            tree=ast.parse(src)
            cls=next(x for x in tree.body if isinstance(x,ast.ClassDef)
                     and x.name=="Handler")
            return {x.name:ast.dump(x,include_attributes=False)
                    for x in cls.body if isinstance(x,ast.FunctionDef)}
        a,b=handler_methods(old),handler_methods(new)
        self.assertEqual(a["do_POST"],b["do_POST"])
        for key in ("_authenticated","_valid_host","_valid_origin",
                    "_handle_publication","_save_friend_scout","_save_friend"):
            self.assertEqual(a[key],b[key])
        self.assertLess(new.index(b'if not self._authenticated()'),
                        new.index(b'elif urlsplit(self.path).path == "/moltbook/social-memory":'))
        self.assertEqual(len(nav)-len(oldnav)>0,True)

if __name__=="__main__":
    unittest.main()
