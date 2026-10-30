"""v0.7.5: synthetic read-only Logs dashboard, no live user journal or network."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
import ast
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for p in ("src/lib/bob","webui","scripts"):
    sys.path.insert(0,str(ROOT/p))

import bob_diagnostic_logs as logs
import bob_job_tracking as tracking
import build_v074_fm3_friend_scout_candidate as before
import build_v075_logs_candidate as candidate

AT=datetime(2026,10,30,4,0,0,tzinfo=timezone.utc)
RID="20261029T224411Z"
SECRET="moltbook_supersecret_token"
POST_TEXT="PRIVATE MOLTPUBLISH DRAFT CONTENT"


def fixture_db(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,state TEXT,"
                   "last_error TEXT,updated_at TEXT)")
        db.execute("CREATE TABLE original_posts(id TEXT PRIMARY KEY,state TEXT,"
                   "last_error TEXT,updated_at TEXT)")
        db.execute("CREATE TABLE original_requests(id TEXT PRIMARY KEY,state TEXT,"
                   "error TEXT,created_at TEXT)")
        db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                   "at TEXT,kind TEXT,details TEXT)")
        t=(AT-timedelta(minutes=10)).isoformat()
        db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",
                   (RID,"failed","Friend-targeted draft requires manual review",t))
        db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",
                   ("20261029T230000Z","uncertain",
                    "Moltbook HTTP 429 "+SECRET+" "+POST_TEXT,t))
        db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",
                   ("20261029T231111Z","failed",SECRET+" "+POST_TEXT,t))
        db.execute("INSERT INTO original_posts VALUES(?,?,?,?)",
                   ("0123456789abcdef01234567","failed","Challenge expired",t))
        db.execute("INSERT INTO original_requests VALUES(?,?,?,?)",
                   ("0123456789abcdef01234568","failed","model prompt "+SECRET,t))
        db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
                   (t,"publish_blocked",RID+" "+SECRET+" "+POST_TEXT))
        db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
                   (t,"new_replies",POST_TEXT+" "+SECRET))
        db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
                   (t,"badprivate","bad "+SECRET+" "+POST_TEXT))
        db.execute("INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)",
                   (t,"other_event",POST_TEXT))


def fake_journal(*,message="SCOUT ERROR: Moltbook HTTP 503 "+SECRET):
    epoch=str(int((AT-timedelta(minutes=5)).timestamp()*1_000_000))
    records=[
        {"MESSAGE":message,"__REALTIME_TIMESTAMP":epoch,
         "_SYSTEMD_USER_UNIT":"bob-moltbook-scout.service"},
        {"MESSAGE":"Bearer "+SECRET+" "+POST_TEXT,
         "__REALTIME_TIMESTAMP":epoch,"_SYSTEMD_USER_UNIT":"bob-moltbook-scout.service"},
        {"MESSAGE":"Main process exited, code=exited, status=1/FAILURE",
         "__REALTIME_TIMESTAMP":epoch,"_SYSTEMD_USER_UNIT":"bob-moltbook-scout.service"},
        {"MESSAGE":"This private post says "+POST_TEXT,
         "__REALTIME_TIMESTAMP":epoch,"_SYSTEMD_USER_UNIT":"bob-moltbook-scout.service"},
    ]
    calls=[]
    def runner(args,*,capture_output,timeout,check):
        calls.append(args)
        assert args[0:4]==["journalctl","--user","--unit","bob-moltbook-scout.service"]
        assert capture_output is True and timeout<=3 and check is False
        class Result:
            returncode=0
            stdout=b"".join((json.dumps(x)+"\n").encode() for x in records)
        return Result()
    return runner,calls


class LogsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.dbpath=self.root/"queue.sqlite3"
        fixture_db(self.dbpath)
        self.cp=self.root/"private-checkpoints"
        self.cp.mkdir(mode=0o700)
        self.cp.chmod(0o700)
        self.assertTrue(tracking.checkpoint("publisher",RID,"failed",root=self.cp))

    def opts(self,**kw):
        defaults={"service":"all","level":"all","source":"all","window":"24h","q":""}
        return {**defaults,**kw}

    def test_safe_job_reasons_and_event_details_never_leak(self):
        result,ok=logs._db_entries(self.dbpath)
        self.assertTrue(ok)
        text="\n".join(r["message"] for r in result)
        self.assertIn("manual review",text)
        self.assertIn("Moltbook HTTP 429",text)
        self.assertIn("Detailed error withheld",text)
        self.assertIn("Verification challenge expired",text)
        self.assertNotIn(SECRET,text)
        self.assertNotIn(POST_TEXT,text)
        self.assertNotIn("badprivate",text)
        blocked=[r for r in result if r["source"]=="jobs" and r["id"]==RID]
        self.assertEqual(len(blocked),1)
        self.assertEqual(blocked[0]["level"],"warning")
        self.assertIn("intentionally blocked",blocked[0]["message"])
        self.assertEqual(len([r for r in result if r["source"]=="events"
                              and r["message"]=="Publication blocked by safety check"]),1)
        self.assertTrue(all(len(x["message"])<=350 for x in result))

    def test_journal_allowlist_redacts_arbitrary_messages_and_secrets(self):
        runner,calls=fake_journal()
        entries,ok=logs._journal_entries("scout",AT-timedelta(days=1),run=runner)
        self.assertTrue(ok)
        messages=" ".join(row["message"] for row in entries)
        self.assertIn("Moltbook HTTP 503",messages)
        self.assertIn("Systemd service failure",messages)
        self.assertNotIn(SECRET,messages)
        self.assertNotIn(POST_TEXT,messages)
        self.assertEqual(len(calls),1)
        self.assertIn("--no-pager",calls[0])
        self.assertIn("--output=json",calls[0])
        self.assertNotIn("sudo",calls[0])
        self.assertNotIn("--system",calls[0])
        self.assertEqual(logs.journal_message("some private post "+SECRET,"test"),None)
        self.assertEqual(logs.journal_message("Traceback (most recent call last)",
                                               "test")[0],"error")

    def test_strict_filter_whitelist_and_bounded_search(self):
        self.assertEqual(logs.options({"service":["sudo rm -rf /"],"level":["secret"],
                                       "window":["forever"],"q":[SECRET*20]}),
                         self.opts())
        self.assertEqual(logs.options({"service":["scout","publisher"]})["service"],"all")
        result,count,_=logs.collect(self.opts(service="publisher",level="warning",
                             source="jobs",q=RID),
                             db_path=self.dbpath,checkpoint_root=self.cp,
                             journal_runner=lambda *a,**kw: self.fail("no journal"),at=AT)
        self.assertEqual(len(result),1)
        self.assertEqual(count,1)
        self.assertEqual(result[0]["id"],RID)
        self.assertIn("manual review",result[0]["message"])
        result,count,_=logs.collect(self.opts(service="publisher",level="error",
                              source="jobs",q="nonsense"),
                              db_path=self.dbpath,checkpoint_root=self.cp,
                              journal_runner=lambda *a,**kw: self.fail("no journal"),at=AT)
        self.assertEqual(result,[])
        self.assertEqual(count,0)
        self.assertEqual(logs.MAX_ROWS,120)

    def test_missing_database_and_unavailable_journal_escapes_safely(self):
        absent=self.root/"missing.sqlite3"
        result,ok=logs._db_entries(absent)
        self.assertEqual(result,[])
        self.assertFalse(ok)
        self.assertFalse(absent.exists())
        link=self.root/"linked.sqlite3"
        link.symlink_to(self.dbpath)
        self.assertEqual(logs._db_entries(link),([],False))
        def broken(*a,**kw):
            raise FileNotFoundError(SECRET)
        rows,ok=logs._journal_entries("scout",AT-timedelta(days=1),run=broken)
        self.assertEqual((rows,ok),([],False))
        html=logs.page(lambda t,b,p:b,{},db_path=absent,checkpoint_root=self.cp,
                       journal_runner=broken,at=AT)
        self.assertIn("database unavailable",html)
        self.assertIn("journal is unavailable",html)
        self.assertNotIn(SECRET,html)

    def test_full_page_filters_and_escapes_untrusted_search(self):
        runner,_=fake_journal()
        html=logs.page(lambda title,body,path:body,
                       {"service":["scout"],"source":["journal"],"level":["error"],
                        "q":["<img src=x onerror=alert(1)>"]},
                       db_path=self.dbpath,checkpoint_root=self.cp,
                       journal_runner=runner,at=AT)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;",html)
        self.assertNotIn("<img src=x",html)
        self.assertIn('name="service"',html)
        self.assertIn('name="level"',html)
        self.assertIn('name="source"',html)
        self.assertIn('name="window"',html)
        self.assertIn("Filter logs",html)
        self.assertIn("Clear filters",html)
        self.assertIn("No entries match these filters",html)
        self.assertNotIn(SECRET,html)
        self.assertNotIn(POST_TEXT,html)
        html=logs.page(lambda t,b,p:b,{"service":["publisher"],"level":["warning"],
                    "source":["jobs"],"q":[RID]},db_path=self.dbpath,
                    checkpoint_root=self.cp,journal_runner=runner,at=AT)
        self.assertIn(RID,html)
        self.assertIn("saved friend requires manual review",html)
        self.assertNotIn(SECRET,html)
        self.assertIn("UTC",html)

    def test_checkpoint_source_uses_existing_safe_notes(self):
        records=logs._checkpoint_entries(root=self.cp)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]["source"],"checkpoints")
        self.assertEqual(records[0]["level"],"error")
        self.assertIn("correlating with stored jobs",records[0]["message"])
        self.assertNotIn("Bearer",records[0]["message"])

    def test_auto_comment_block_labelled_warning_not_publication_failure(self):
        with sqlite3.connect(self.dbpath) as db:
            t=(AT-timedelta(minutes=2)).isoformat()
            db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",
                       ("20261029T224412Z","failed","Human decision already exists",t))
        rows,available=logs._db_entries(self.dbpath)
        self.assertTrue(available)
        block=next(row for row in rows if row["id"]=="20261029T224412Z"
                   and row["source"]=="jobs")
        self.assertEqual(block["level"],"warning")
        self.assertIn("owner review decision",block["message"])
        self.assertIn("not sent",block["message"])
        self.assertIn("database state: failed",block["message"])

    def test_failed_checkpoint_correlates_same_run_job_and_does_not_repeat_inspect_logs(self):
        with sqlite3.connect(self.dbpath) as db:
            t=(AT-timedelta(minutes=2)).isoformat()
            db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",
                       ("20261029T224412Z","failed","Human decision already exists",t))
        synthetic=dict(worker="publisher",job_id="20261029T224412Z",
                       stage="failed",message="Worker step failed; inspect logs",
                       updated_at=(AT-timedelta(minutes=2)).isoformat(),
                       stale=False)
        with patch.object(logs,"read_checkpoints",return_value=[synthetic]):
            result,count,_=logs.collect(self.opts(source="checkpoints",
                            service="publisher",level="warning"),
                            db_path=self.dbpath,
                            journal_runner=lambda *args,**kw: type("Result",(),{
                                "returncode":1,"stdout":b""})(),
                            at=AT)
        self.assertEqual(count,1)
        self.assertEqual(result[0]["source"],"checkpoints")
        self.assertIn("owner review decision",result[0]["message"])
        self.assertNotIn("inspect logs",result[0]["message"])
        self.assertEqual(result[0]["level"],"warning")

    def test_scout_checkpoint_time_correlates_sanitized_journal_without_false_certainty(self):
        synthetic=dict(worker="scout",job_id=RID,
                       stage="failed",message="Worker step failed; inspect logs",
                       updated_at=(AT-timedelta(minutes=5)).isoformat(),
                       stale=False)
        runner,_=fake_journal()
        with patch.object(logs,"read_checkpoints",return_value=[synthetic]):
            result,count,sources=logs.collect(self.opts(source="checkpoints",
                                         service="scout",level="error"),
                                         db_path=self.dbpath,
                                         journal_runner=runner,at=AT)
        self.assertTrue(sources["journal"])
        self.assertEqual(count,1)
        self.assertIn("Moltbook HTTP 503",result[0]["message"])
        self.assertIn("not a proven cause",result[0]["message"])
        self.assertNotIn(SECRET,result[0]["message"])
        self.assertNotIn("inspect logs",result[0]["message"])

    def test_unavailable_journal_gives_explicit_unknown_cause(self):
        synthetic=dict(worker="scout",job_id=RID,
                       stage="failed",message="Worker step failed; inspect logs",
                       updated_at=(AT-timedelta(minutes=5)).isoformat(),
                       stale=False)
        with patch.object(logs,"read_checkpoints",return_value=[synthetic]):
            result,count,sources=logs.collect(self.opts(source="checkpoints",
                                         service="scout",level="error"),
                                         db_path=self.dbpath,
                                         journal_runner=lambda *args,**kw: (_ for _ in ()).throw(
                                             OSError("SECRET IN EXECUTION")),at=AT)
        self.assertEqual(count,1)
        self.assertFalse(sources["journal"])
        self.assertIn("cause is unknown",result[0]["message"])
        self.assertNotIn("inspect logs",result[0]["message"])
        self.assertNotIn("SECRET",result[0]["message"])

    def test_builder_adds_only_readonly_get_branch_and_navigation(self):
        old,oldnav=before.build()
        new,nav=candidate.build()
        self.assertIn(b'urlsplit(self.path).path == "/logs"',new)
        self.assertIn(b'from bob_diagnostic_logs import page as diagnostics_page',new)
        self.assertIn(b'/logs',nav)
        self.assertNotIn(b'/logs',oldnav)
        tree_before=ast.parse(old)
        tree_after=ast.parse(new)
        def methods(tree):
            cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="Handler")
            return {m.name:ast.dump(m,include_attributes=False) for m in cls.body
                    if isinstance(m,ast.FunctionDef)}
        oldmethods,newmethods=methods(tree_before),methods(tree_after)
        self.assertEqual(set(oldmethods),set(newmethods))
        for name in oldmethods:
            if name not in ("do_GET","_error_page"):
                self.assertEqual(oldmethods[name],newmethods[name],name)
        self.assertNotIn(b'if path == "/logs":',new)
        self.assertIn(b'self._send(200, diagnostics_page(wrap,',new)
        compile(new,"generated-activity-manager","exec")
        compile(nav,"generated-navigation-shell","exec")


if __name__=="__main__":
    unittest.main()
