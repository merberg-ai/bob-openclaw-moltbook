"""OC3 offline safety acceptance: source-classified console and safe export.

No live services, raw logs, credentials, private prompts or publication.
Synthetic SQLite, injected read-only status and user-systemd journal executor.
"""
from __future__ import annotations
import ast
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for x in ("scripts","src/lib/bob","webui"):
    sys.path.insert(0,str(ROOT/x))
import bob_diagnostic_console as console
import bob_diagnostic_logs as logs
import build_v076_oc2_candidate as previous
import build_v076_oc3_candidate as candidate

AT=datetime(2026,10,30,15,0,tzinfo=timezone.utc)
SECRET="TOP_SECRET_PRIVATE_42"
POST="PUBLIC_POST_TITLE_PRIVATE"
TOKEN="sk-abcdef-superprivate"

def db_fixture(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,state TEXT,"
                   "last_error TEXT,updated_at TEXT)")
        db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",(
            "20261030T140000Z","failed","Friend-targeted draft requires manual review",
            "2026-10-30T14:00:00+00:00"))
        db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",(
            "20261030T143000Z","uncertain","Raw "+SECRET+" "+POST+" "+TOKEN,
            "2026-10-30T14:30:00+00:00"))
        db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?)",(
            "20261030T144000Z",SECRET,"", "2026-10-30T14:40:00+00:00"))
        db.execute("CREATE TABLE original_posts(id TEXT,state TEXT,last_error TEXT,updated_at TEXT)")
        db.execute("CREATE TABLE original_requests(id TEXT,state TEXT,error TEXT,created_at TEXT)")
        db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY,at TEXT,kind TEXT,details TEXT)")
        db.execute("INSERT INTO publish_events VALUES(1,?,?,?)",(
            "2026-10-30T14:32:00+00:00","publish_blocked",SECRET+" "+TOKEN))
        db.execute("INSERT INTO publish_events VALUES(2,?,?,?)",(
            "2026-10-30T14:37:00+00:00","auto_queued",POST+" "+TOKEN))

def health_snapshot():
    return {"services":[
        {"name":"Gateway","state":"running"},
        {"name":"Gateway port","state":"listening"},
        {"name":"Ollama","state":"ready"},
        {"name":"Scout timer","state":"running"},
        {"name":"Publisher timer","state":"inactive"},
        {"name":SECRET,"state":"running"},
        {"name":"Activity Manager","state":SECRET},
    ]}

class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dbpath=Path(self.tmp.name)/"queue.sqlite3"
        db_fixture(self.dbpath)

    def opts(self,**changes):
        return {**console.options({}),**changes}

    def collect(self,**changes):
        with patch.object(logs,"_checkpoint_entries",return_value=[]):
            return console.collect(self.opts(**changes),db_path=self.dbpath,
                 at=AT,health_provider=health_snapshot)

    def test_default_stream_is_sanitized_and_never_reads_journal(self):
        with patch.object(logs,"_journal_entries",side_effect=AssertionError("No default journal allowed")), \
             patch.object(logs,"_checkpoint_entries",return_value=[]):
            data=console.collect(self.opts(),db_path=self.dbpath,
                at=AT,health_provider=health_snapshot)
        self.assertGreater(len(data["entries"]),3)
        self.assertTrue(any(x["source"]=="health" and x["service"]=="ollama"
                            for x in data["entries"]))
        self.assertTrue(any(x["source"]=="jobs" for x in data["entries"]))
        self.assertTrue(any(x["source"]=="events" for x in data["entries"]))
        serialized=json.dumps(data)
        for phrase in (SECRET,POST,TOKEN):
            self.assertNotIn(phrase,serialized)
        self.assertNotIn("prompt",serialized.lower())
        self.assertIn("Stored job state is unrecognized; details withheld",serialized)
        self.assertEqual(data["journal_explicit_only"],True)
        self.assertIsNone(data["sources"]["journal"])
        self.assertTrue(data["sources"]["database"])

    def test_strict_service_level_source_query_window_allowlists(self):
        params={"service":["../etc/passwd"],"source":["../../secrets"],
                "level":["shell"],"window":["3650d"],"q":[SECRET*30]}
        opt=console.options(params)
        self.assertEqual(opt["service"],"all")
        self.assertEqual(opt["source"],"all")
        self.assertEqual(opt["window"],"24h")
        self.assertEqual(opt["q"],"")
        self.assertEqual(console.options({"source":["journal","health"]})["source"],"all")
        self.assertEqual(console.options({"service":["ollama"]})["service"],"ollama")
        self.assertNotIn(SECRET,console.params_url(opt))

    def test_journal_requires_explicit_source_and_allowlisted_units(self):
        calls=[]
        def executor(args,**kw):
            calls.append(args)
            class Result:
                returncode=0
                stdout=b""
            return Result()
        with patch.object(logs,"_checkpoint_entries",return_value=[]):
            data=console.collect(self.opts(source="journal",service="gateway"),
                db_path=self.dbpath,at=AT,journal_runner=executor,
                health_provider=health_snapshot)
            self.assertEqual(len(calls),1)
            self.assertIn("openclaw-gateway.service",calls[0])
            self.assertEqual(calls[0][:4],["journalctl","--user","--unit","openclaw-gateway.service"])
            self.assertNotIn("shell",str(calls[0]))
            self.assertEqual(data["entries"],[])
            self.assertTrue(data["sources"]["journal"])
            calls.clear()
            blocked=console.collect(self.opts(source="journal",service="ollama"),
                db_path=self.dbpath,at=AT,journal_runner=executor)
            self.assertEqual(calls,[])
            self.assertFalse(blocked["sources"]["journal"])

    def test_filtering_severity_source_and_time(self):
        errors=self.collect(level="error")
        self.assertTrue(all(x["level"]=="error" for x in errors["entries"]))
        self.assertTrue(any(x["service"]=="publisher" for x in errors["entries"]))
        health=self.collect(source="health",service="ollama")
        self.assertEqual(len(health["entries"]),1)
        self.assertEqual(health["entries"][0]["message"],"Ollama: ready")
        self.assertEqual(self.collect(service="gateway",source="jobs")["entries"],[])
        self.assertEqual(self.collect(q="publication blocked",source="events")["entries"][0]["service"],
                         "publisher")
        self.assertEqual(self.collect(window="24h",q="nonexistent-xyz")["entries"],[])

    def test_html_escapes_unsafe_search_and_uses_only_same_origin_assets(self):
        opts={"q":['<img src=x onerror="alert(1)">']}
        html=console.page(lambda title,body,route:body,opts,
                          collector=lambda opt:self.collect())
        self.assertIn("Diagnostic Console",html)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",html)
        self.assertNotIn("<img src=x onerror",html)
        self.assertIn('src="/assets/bob-console.js"',html)
        self.assertIn('href="/api/dashboard/console?',html)
        self.assertIn('download="bob-console-sanitized.txt"',html)
        self.assertIn("No prompt text",html)
        self.assertNotIn(SECRET,html)
        self.assertIn("bco-screen",html)
        self.assertIn("@media(max-width:590px)",console.CSS)

    def test_plaintext_export_only_contains_same_safe_messages_and_is_bounded(self):
        data=self.collect()
        out=console.export_text(data)
        self.assertLessEqual(len(out),console.MAX_TEXT_BYTES+1)
        for phrase in (SECRET,POST,TOKEN):
            self.assertNotIn(phrase,out)
        self.assertIn("Bob Diagnostic Console (sanitized, read-only)",out)
        self.assertIn("Ollama: ready",out)
        self.assertNotIn("Raw "+SECRET,out)

    def test_missing_data_does_not_fabricate_success_and_journal_stays_opt_in(self):
        with patch.object(logs,"_checkpoint_entries",return_value=[]):
            val=console.collect(self.opts(),db_path=Path(self.tmp.name)/"missing",
               at=AT,health_provider=lambda: (_ for _ in ()).throw(OSError("secrets")))
        self.assertEqual(val["entries"],[])
        self.assertFalse(val["sources"]["database"])
        self.assertFalse(val["sources"]["health"])
        self.assertIsNone(val["sources"]["journal"])

    def test_default_js_is_safe_visible_bounded_and_manual_journal(self):
        js=console.javascript()
        self.assertIn("setInterval(",js)
        self.assertIn("45000",js)
        self.assertIn("document.hidden",js)
        self.assertIn("find('source').value!=='journal'",js)
        self.assertIn("screen.replaceChildren(",js)
        self.assertIn("textContent=",js)
        self.assertIn("credentials:'same-origin'",js)
        self.assertNotIn("innerHTML",js)
        self.assertNotIn("fetch('/api/dashboard/console' + ",js)
        self.assertNotIn("method:'POST'",js)
        self.assertIn("Pause updates",js)
        self.assertIn("Copy safe lines",console.page(lambda a,b,c:b,{},collector=lambda _: {
            "checked_at":AT.isoformat(),"entries":[],"matched":0,"sources":{}}))

    def test_pinned_manager_only_adds_authenticated_get_routes_and_console_csp(self):
        old,oldnav=previous.build()
        new,nav=candidate.build()
        compile(new,"manager","exec")
        compile(nav,"navigation_shell.py","exec")
        self.assertIn(b'elif urlsplit(self.path).path == "/console":',new)
        self.assertIn(b'elif urlsplit(self.path).path == "/api/dashboard/console":',new)
        self.assertIn(b'elif self.path == "/assets/bob-console.js":',new)
        self.assertIn(b'query.get("format")==["text"]',new)
        self.assertIn(b'("/console", "Console",',nav)
        self.assertIn(b'"/mind/personality", "/console")',new)
        def methods(src):
            tree=ast.parse(src)
            cls=next(x for x in tree.body if isinstance(x,ast.ClassDef)
                     and x.name=="Handler")
            return {x.name:ast.dump(x,include_attributes=False) for x in cls.body
                    if isinstance(x,ast.FunctionDef)}
        a,b=methods(old),methods(new)
        self.assertEqual(a["do_POST"],b["do_POST"])
        for key in ("_handle_publication","_save_friend_scout","_handle_original",
                    "_authenticated","_valid_host","_valid_origin"):
            self.assertEqual(a[key],b[key],key)
        self.assertLess(new.index(b'if not self._authenticated()'),
                        new.index(b'elif urlsplit(self.path).path == "/console":'))
        self.assertNotIn(b'if path == "/console":',new)


if __name__=="__main__":
    unittest.main()
