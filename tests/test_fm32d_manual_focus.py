"""FM3.2d bounded explicit inspection of one saved watched public friend.

All tests use synthetic local DB and injected API/model. No real Moltbook
fetches, Ollama requests, host service changes or publication.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
for folder in ("src/lib/bob","scripts","webui"):
    sys.path.insert(0,str(ROOT/folder))
import bob_friend_scout as scout
import bob_friends as friends
import bob_publish_common as common
import build_v075_fm32c_candidate as prior
import build_v075_fm32d_candidate as latest

AID="01234567-89ab-cdef-0123-456789abcdef"
PID1="11111111-2222-3333-4444-555555555555"
PID2="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def model_result():
    return {"proposal":{"source_post_id":PID1,
                        "interest":"I may want to compare how agents assess evidence.",
                        "reason":"Their public post discusses belief revision.",
                        "uncertainty":"I cannot verify the author's general claims.",
                        "confidence":"low"}}


class FocusTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        for name,value in (("DATA",self.root),("DB",self.root/"queue.sqlite3")):
            p=patch.object(common,name,value)
            p.start()
            self.addCleanup(p.stop)
        with common.connect() as db:
            self.fid=friends.create(db,"Agent01",dict(
                display_name="One",relationship="interesting",
                interests="PRIVATE-INTERESTS",notes="PRIVATE-NOTES"))
            self.other=friends.create(db,"Agent02",dict(
                display_name="Two",relationship="acquaintance",
                interests="PRIVATE-OTHER",notes="PRIVATE-MORE"))
            scout.change(db,dict(csrf="t",enabled="1",expected="0",
                                 confirmation=scout.CONFIRM))

    def db(self):
        return common.connect()

    def form(self,fid=None):
        with self.db() as db:
            item=friends._get(db,fid or self.fid)
            return dict(csrf="t",operation="focus_inspect",id=item["id"],
                        friend_sha=item["sha256"],watch_sha="default",
                        confirmation=scout.FOCUS_CONFIRM)

    def start(self,fid=None):
        with self.db() as db:
            v=scout.change(db,self.form(fid))
            self.assertTrue(v.startswith("focus-job:"))
            return v[10:]

    def job(self,ident):
        with self.db() as db:
            return scout._focus_get(db,ident)

    def fake_get(self):
        calls=[]
        def getter(path):
            calls.append(path)
            if path.startswith("/api/v1/agents/profile?"):
                return dict(success=True,agent={"name":"Agent01","id":AID,
                    "description":"<script>untrusted text</script>"},
                    recentPosts=[{"id":PID1},{"id":PID2},{"id":"cccccccc-dddd-eeee-ffff-000000000000"}])
            pid=path.removeprefix("/api/v1/posts/")
            return {"success":True,"post":{"id":pid,"title":"<img src=x onerror=alert(1)>",
                "content":"Interesting public discussion of learning and memory",
                "author":{"name":"Agent01","id":AID}}}
        return getter,calls

    def test_explicit_confirmation_global_switch_and_pauses(self):
        with self.db() as db:
            form=self.form()
            form["confirmation"]="NO"
            with self.assertRaisesRegex(ValueError,"confirmation"):
                scout.change(db,form)
            form=self.form()
            form["extra"]="bad"
            with self.assertRaisesRegex(ValueError,"form invalid"):
                scout.change(db,form)
            friend=friends._get(db,self.fid)
            scout.change(db,dict(csrf="t",operation="watch",id=self.fid,
                                 friend_sha=friend["sha256"],watch_sha="default",
                                 watch_enabled="0"))
            with self.assertRaisesRegex(ValueError,"source changed|watched"):
                scout.change(db,self.form())
            friend=friends._get(db,self.fid)
            prefs=scout._preferences(db)[self.fid]
            scout.change(db,dict(csrf="t",operation="watch",id=self.fid,
                                 friend_sha=friend["sha256"],
                                 watch_sha=prefs["sha256"],watch_enabled="1"))
            form=self.form()
            with self.assertRaisesRegex(ValueError,"source changed"):
                scout.change(db,form)
            scout.change(db,dict(csrf="t",enabled="0",expected="1",confirmation=""))
            with self.assertRaisesRegex(ValueError,"requires friend scouting enabled"):
                scout.change(db,self.form())

    def test_capped_fixed_host_reads_profile_id_post_id_and_author(self):
        getter,calls=self.fake_get()
        friend={"handle":"Agent01","handle_key":"agent01"}
        result=scout.focus_fetch(friend,getter=getter)
        self.assertEqual(len(calls),3)
        self.assertEqual(calls[0],"/api/v1/agents/profile?name=Agent01")
        self.assertEqual(calls[1],"/api/v1/posts/"+PID1)
        self.assertEqual(calls[2],"/api/v1/posts/"+PID2)
        self.assertEqual([p["id"] for p in result["posts"]],[PID1,PID2])
        self.assertEqual(result["agent_id"],AID)
        def spoof(path):
            x=getter(path)
            if path.startswith("/api/v1/agents"):
                x["agent"]["name"]="Unrelated"
            return x
        with self.assertRaisesRegex(ValueError,"profile unavailable"):
            scout.focus_fetch(friend,getter=spoof)
        def wrongid(path):
            x=getter(path)
            if path.startswith("/api/v1/posts"):
                x["post"]["author"]["id"]="not-matching"
            return x
        self.assertEqual(scout.focus_fetch(friend,getter=wrongid)["posts"],[])
        def badpost(path):
            x=getter(path)
            if path.startswith("/api/v1/posts"):
                x["post"]["author"]["name"]="Other"
            return x
        self.assertEqual(scout.focus_fetch(friend,getter=badpost)["posts"],[])

    def test_worker_stores_private_snapshot_and_reviewed_tentative_reaction(self):
        ident=self.start()
        getter,_=self.fake_get()
        with patch.object(scout,"_json_get",side_effect=getter) as fetch, \
             patch.object(scout,"_ai_model",return_value=model_result()) as ai:
            scout.focus_worker(ident,common.connect)
            self.assertEqual(fetch.call_count,3)
            ai.assert_called_once()
            self.assertEqual(ai.call_args[0][0]["run_id"],"manual-focus:"+ident)
        job=self.job(ident)
        self.assertEqual(job["status"],"completed")
        self.assertEqual(job["review_status"],"pending")
        self.assertEqual(json.loads(job["result_json"])["posts"][0]["id"],PID1)
        self.assertTrue(scout.focus_valid(job))
        with self.db() as db:
            html=scout.page(db,"csrf",lambda t,b,p:b,[])
            self.assertIn("&lt;img src=x onerror=alert(1)&gt;",html)
            self.assertNotIn("<img src=x onerror",html)
            self.assertNotIn("<script>",html)
            self.assertNotIn("PRIVATE-INTERESTS",html)
            self.assertNotIn("PRIVATE-NOTES",html)
            form=dict(csrf="csrf",operation="focus_review",id=ident,
                      expected_sha=job["sha256"],decision="approve",
                      reason="This might be a useful topic")
            self.assertEqual(scout.change(db,form),"approved")
            with self.assertRaisesRegex(ValueError,"changed"):
                scout.change(db,form)
            reviewed=scout._focus_get(db,ident)
            reopened={**form,"expected_sha":reviewed["sha256"],
                      "decision":"reopen","reason":"Reconsider later"}
            self.assertEqual(scout.change(db,reopened),"pending")
            with self.assertRaisesRegex(ValueError,"changed"):
                scout.change(db,form)
            self.assertEqual(db.execute("SELECT count(*) FROM bob_friend_focus_history "
                       "WHERE id=?",(ident,)).fetchone()[0],5)
            self.assertEqual(db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM decisions").fetchone()[0],0)
            self.assertEqual(friends._get(db,self.fid)["notes"],"PRIVATE-NOTES")
            self.assertTrue(scout.enabled(db))

    def test_one_job_global_cooldown_per_friend_and_failure_counts(self):
        ident=self.start()
        with self.db() as db:
            with self.assertRaisesRegex(ValueError,"already active"):
                scout.change(db,self.form(self.other))
            scout._focus_fail(db,ident,"profile_unavailable")
            with self.assertRaisesRegex(ValueError,"cooling down"):
                scout.change(db,self.form(self.other))
            with self.assertRaisesRegex(ValueError,"cooling down"):
                scout.change(db,self.form(self.fid))
            job=scout._focus_get(db,ident)
            job["created_at"]=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
            scout._focus_update(db,job,"synthetic-age")
            with self.assertRaisesRegex(ValueError,"cooling down"):
                scout.change(db,self.form(self.fid))
            self.assertTrue(scout.change(db,self.form(self.other)).startswith("focus-job:"))

    def test_pause_while_job_running_prevents_completing_snapshot(self):
        ident=self.start()
        getter,_=self.fake_get()
        original_fetch=scout.focus_fetch
        def after_profile(friend):
            with self.db() as db:
                f=friends._get(db,self.fid)
                scout.change(db,dict(csrf="t",operation="watch",id=self.fid,
                                     friend_sha=f["sha256"],watch_sha="default",
                                     watch_enabled="0"))
            return original_fetch(friend,getter=getter)
        with patch.object(scout,"focus_fetch",side_effect=after_profile), \
             patch.object(scout,"_ai_model") as ai:
            scout.focus_worker(ident,common.connect)
            ai.assert_not_called()
        job=self.job(ident)
        self.assertEqual(job["status"],"failed")
        self.assertEqual(job["error_code"],"source_changed")
        self.assertEqual(job["result_json"],"")

    def test_no_reaction_or_unavailable_model_keeps_readonly_snapshot(self):
        ident=self.start()
        getter,_=self.fake_get()
        with patch.object(scout,"_json_get",side_effect=getter), \
             patch.object(scout,"_ai_model",side_effect=OSError("offline")):
            scout.focus_worker(ident,common.connect)
        job=self.job(ident)
        self.assertEqual(job["status"],"completed")
        self.assertEqual(job["review_status"],"none")
        self.assertEqual(job["idea_json"],"")
        with self.db() as db:
            html=scout.page(db,"csrf",lambda t,b,p:b,[])
            self.assertIn("Local Ollama reaction unavailable or not useful",html)
            self.assertNotIn("PRIVATE-NOTES",html)

    def test_forged_record_digest_and_stale_or_invalid_review_blocked(self):
        ident=self.start()
        getter,_=self.fake_get()
        with patch.object(scout,"_json_get",side_effect=getter), \
             patch.object(scout,"_ai_model",return_value=model_result()):
            scout.focus_worker(ident,common.connect)
        job=self.job(ident)
        with self.db() as db:
            form=dict(csrf="t",operation="focus_review",id=ident,
                      expected_sha="0"*64,decision="approve",reason="valid reason")
            with self.assertRaisesRegex(ValueError,"changed"):
                scout.change(db,form)
            db.execute("UPDATE bob_friend_focus_jobs SET idea_json='{\"untrusted\":true}' "
                       "WHERE id=?",(ident,))
            with self.assertRaisesRegex(ValueError,"unavailable"):
                scout.change(db,{**form,"expected_sha":job["sha256"]})
            self.assertFalse(any(x["id"]==ident for x in scout._focus_recent(db)))

    def test_interrupted_jobs_are_never_replayed_automatically(self):
        ident=self.start()
        with self.db() as db:
            job=scout._focus_get(db,ident)
            job["updated_at"]="2000-01-01T00:00:00+00:00"
            scout._focus_update(db,job,"age")
            # _focus_update rewrites the updated timestamp; shift directly via
            # hash-consistent synthetic job update using a known past time.
            job=scout._focus_get(db,ident)
            job["status"]="failed"
            job["error_code"]="interrupted"
            scout._focus_update(db,job,"manual-interrupted")
        with patch.object(scout,"focus_fetch") as remote:
            scout.focus_worker(ident,common.connect)
            remote.assert_not_called()

    def test_manager_builder_exact_delta_preserves_auth_and_limit(self):
        old,oldnav=prior.build()
        new,newnav=latest.build()
        self.assertEqual(oldnav,newnav)
        code=new.decode()
        self.assertIn("name='bob-friend-focus'",code)
        self.assertIn("max_num_fields=6",code)
        self.assertIn("if not self._valid_origin():",code)
        reverted=code.replace(
            "interest_ai_worker as friend_interest_ai_worker, "
            "focus_worker as friend_focus_worker)",
            "interest_ai_worker as friend_interest_ai_worker)")
        reverted=reverted.replace(
            "            if isinstance(outcome,str) and outcome.startswith('focus-job:'):\n"
            "                threading.Thread(target=friend_focus_worker,\n"
            "                    args=(outcome[10:],publish_conn),daemon=True,\n"
            "                    name='bob-friend-focus').start()\n","")
        self.assertEqual(reverted.encode(),old)


if __name__=="__main__":
    unittest.main()
