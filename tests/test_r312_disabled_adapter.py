"""R3.12 disabled-by-default real publisher selector + fake credentialed POST.

All databases are private test fixtures. The legacy publisher is loaded from
the actual executable, but network and credential methods are replaced by
strict fakes before every call. No production files, API calls or permissions.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.machinery
import importlib.util
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT/"src"), str(ROOT/"src"/"lib"/"bob"),
    str(ROOT/"tests"),
]
from bob_r312_adapter import (
    R312_REAL_DISPATCH, LEGACY_QUEUE_HEAD,
    candidate_dispatch_is_enabled, legacy_queue_head, held_r3_count,
)
from bob_v08.core import Action
from bob_v08.r312_fake_credentialed import (
    run_fake_credentialed, FakeCredentialedTransport, FAKE_KEY,
)
from bob_v08.r311_inert_entry import DESCRIPTOR, recover_inert_entry
from bob_v08.r38_dispatch_lab import SimulatedPowerLoss
from bob_v08.r3_cutover_rehearsal import verified_source
from bob_v08.r3_unified import UnifiedLab, _validated
from test_r3_cutover_rehearsal import make_saved_scout
from test_r3_unified import fixture, consent_policy, RUN, ID, TEXT, NOW

PUBLISHER = ROOT/"src"/"bin"/"bob-moltbook-publisher"


def load_actual_publisher():
    loader = importlib.machinery.SourceFileLoader(
        "bob_publisher_r312_isolated", str(PUBLISHER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class R312AdapterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root/"scout"
        make_saved_scout(self.source)
        self.action = Action("comment", RUN, ID, "Technical explanation.", TEXT)
        self.obs, _ = verified_source(self.source, self.action)
        self.path = self.root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
        fixture(self.path)
        self.lab = UnifiedLab(self.path)
        with sqlite3.connect(self.path) as con:
            con.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
        self.assertEqual(self.lab.propose(self.action, self.obs, at=NOW).state,
                         "proposed")
        self.assertEqual(self.lab.queue(self.action, self.obs, mode="auto",
                        at=NOW, policy=consent_policy()).state, "queued_simulated")
        descriptor = self.root/DESCRIPTOR
        descriptor.write_text(json.dumps({
            "run_id":RUN, "post_id":ID,
            "reason":self.action.reason, "text":TEXT}), encoding="utf-8")
        os.chmod(descriptor, 0o600)

    def rows(self):
        with sqlite3.connect(self.path) as con:
            return con.execute("SELECT run_id,state,attempted_at,comment_id "
                               "FROM publish_jobs ORDER BY run_id").fetchall()

    def inprocess_publisher(self, **patches):
        mod = load_actual_publisher()
        fake_network = []
        def never_api(*args, **kwargs):
            fake_network.append((args, kwargs))
            raise AssertionError("real network path must never be reached")
        def never_key():
            raise AssertionError("real credential path must never be reached")
        mod.api = patches.pop("api", never_api)
        mod.api_key = patches.pop("api_key", never_key)
        mod.auto_candidates = lambda db: 0
        mod.checkpoint = lambda *a, **k: None
        for k,v in patches.items():
            setattr(mod,k,v)
        return mod, fake_network

    def subprocess_cli(self, arg="--r312-fake-credentialed", dbpath=None):
        env = os.environ.copy()
        env["HOME"] = str(self.root)
        env["PYTHONPATH"] = os.pathsep.join([
            str(ROOT/"src"), str(ROOT/"src"/"lib"/"bob"),
            env.get("PYTHONPATH","")])
        return subprocess.run(
            [sys.executable, str(PUBLISHER), arg, str(dbpath or self.path)],
            env=env, capture_output=True, text=True, timeout=15, check=False)

    def test_actual_default_publisher_holds_r3_and_does_not_mark_failed(self):
        module, calls = self.inprocess_publisher()
        with sqlite3.connect(self.path) as con:
            status = module.publisher_step(con)
        self.assertIn("R3 Bob-authored queued drafts held", status)
        self.assertEqual(calls, [])
        self.assertEqual(self.rows(), [(RUN,"queued",None,None)])
        self.assertFalse(R312_REAL_DISPATCH)

    def test_stored_r3_auto_flags_cannot_override_hardcoded_off(self):
        with sqlite3.connect(self.path) as con:
            self.assertEqual(held_r3_count(con),1)
            self.assertFalse(candidate_dispatch_is_enabled(con))
            con.execute("UPDATE publish_settings SET value='1' "
                        "WHERE name='r3_auto_enabled'")
            con.execute("UPDATE publish_settings SET value='auto' "
                        "WHERE name='r3_comment_dial'")
            self.assertFalse(candidate_dispatch_is_enabled(con))
        module, calls=self.inprocess_publisher()
        with sqlite3.connect(self.path) as con:
            self.assertIn("held",module.publisher_step(con))
        self.assertEqual(calls,[])
        self.assertIsNone(self.rows()[0][2])

    def test_existing_legacy_manual_publisher_still_uses_original_post_path(self):
        rid=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        # Must not collide with R3 synthetic source run.
        self.assertNotEqual(rid,RUN)
        pid="33333333-3333-4333-8333-333333333333"
        digest="a"*64
        oldtext="Original approved legacy Scout draft."
        with sqlite3.connect(self.path) as con:
            con.execute("INSERT INTO decisions VALUES(?,?,?,?)",
                        (rid,digest,"approved",datetime.now(timezone.utc).isoformat()))
            con.execute(
                "INSERT INTO publish_jobs(run_id,approval_sha256,post_id,"
                "draft_comment,mode,state,created_at,updated_at)"
                " VALUES(?,?,?,?,?,'queued',?,?)",
                (rid,digest,pid,oldtext,"manual",
                 datetime.now(timezone.utc).isoformat(),
                 datetime.now(timezone.utc).isoformat()))
        fake_calls=[]
        def api(method,path,payload=None,*,key=None):
            fake_calls.append((method,path))
            if method=="GET":
                return {"post":{"id":pid}}
            if method=="POST" and key=="fake-only-test-key":
                self.assertEqual(payload,{"content":oldtext})
                return {"success":True,"comment":{"id":ID}}
            raise AssertionError("unsupported fake request")
        record = {"approval_sha256":digest,
                  "chosen_post_id":pid,"draft_comment":oldtext}
        module,_=self.inprocess_publisher(
            api=api, api_key=lambda:"fake-only-test-key",
            load_record=lambda key:record if key==rid else None)
        with sqlite3.connect(self.path) as con:
            result=module.publisher_step(con)
        self.assertIn("comment published",result)
        self.assertEqual(fake_calls,[("GET","/posts/"+pid),
                                     ("POST","/posts/"+pid+"/comments")])
        with sqlite3.connect(self.path) as con:
            legacy=con.execute("SELECT state,comment_id,attempted_at "
                               "FROM publish_jobs WHERE run_id=?",(rid,)).fetchone()
            r3=con.execute("SELECT state,attempted_at FROM publish_jobs "
                           "WHERE run_id=?",(RUN,)).fetchone()
        self.assertEqual(legacy[:2],("published",ID))
        self.assertIsNotNone(legacy[2])
        self.assertEqual(r3,("queued",None))

    def test_no_additive_schema_uses_original_legacy_query_shape(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE publish_jobs("
                       "run_id TEXT,approval_sha256 TEXT,post_id TEXT,"
                       "draft_comment TEXT,mode TEXT,state TEXT,created_at TEXT)")
            db.execute("INSERT INTO publish_jobs VALUES(?,?,?,?,?,?,?)",
                       ("legacy", "a"*64, ID,"old draft","manual","queued",
                        "2026-10-30T20:00:00Z"))
            expected=db.execute(LEGACY_QUEUE_HEAD).fetchone()
            self.assertEqual(legacy_queue_head(db),expected)
            self.assertEqual(held_r3_count(db),0)

    def test_corrupt_r3_table_fails_closed_before_any_legacy_send(self):
        with sqlite3.connect(self.path) as con:
            con.execute("DROP TABLE r3_proposals")
            con.execute("CREATE TABLE r3_proposals(source_run TEXT PRIMARY KEY)")
        module,calls=self.inprocess_publisher()
        with sqlite3.connect(self.path) as con:
            with self.assertRaisesRegex(ValueError,"r312_untrusted_proposal_schema"):
                module.publisher_step(con)
        self.assertEqual(calls,[])

    def test_real_publisher_cli_runs_one_fake_credentialed_post(self):
        completed=self.subprocess_cli()
        self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
        body=json.loads(completed.stdout)
        self.assertEqual(body["state"],"acknowledged_simulated")
        self.assertEqual(body["fake_post_calls"],1)
        self.assertTrue(body["attempt_recorded"])
        self.assertFalse(body["dispatch_authorized"])
        self.assertFalse(body["acted"])
        self.assertFalse(body["cutover_authorized"])
        self.assertEqual(body["external_requests"],0)
        self.assertEqual(body["production_credential_reads"],0)
        self.assertEqual(body["installed_changes"],0)
        self.assertNotIn(TEXT,completed.stdout)
        self.assertNotIn(FAKE_KEY,completed.stdout)
        self.assertNotIn(str(self.path),completed.stdout)
        self.assertEqual(self.rows()[0][1],"acknowledged_simulated")

    def test_cli_repeated_fake_post_cannot_retry(self):
        self.assertEqual(self.subprocess_cli().returncode,0)
        subsequent=self.subprocess_cli()
        self.assertNotEqual(subsequent.returncode,0)
        report=json.loads(subsequent.stdout)
        self.assertEqual(report["state"],"refused")
        self.assertEqual(report["fake_post_calls"],0)
        with sqlite3.connect(self.path) as con:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM r3_lab_audit WHERE event='r310_claim'"
            ).fetchone()[0],1)

    def test_missing_owner_r3_dial_denies_fake_post_while_legacy_auto_on(self):
        with sqlite3.connect(self.path) as con:
            con.execute("DELETE FROM publish_settings WHERE name IN "
                        "('r3_auto_enabled','r3_comment_dial')")
        result=self.subprocess_cli()
        self.assertEqual(json.loads(result.stdout)["reason"],
                         "review_owner_r3_dial_off")
        self.assertIsNone(self.rows()[0][2])

    def test_real_live_sqlite_path_cannot_use_fake_rehearsal_mode(self):
        other=self.root/"activity-queue.sqlite3"
        result=self.subprocess_cli(dbpath=other)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout)["reason"],
                         "invalid_private_inert_fixture")
        self.assertFalse(other.exists())
        self.assertIsNone(self.rows()[0][2])

    def test_fake_transport_checks_exact_fake_key_and_request_shape(self):
        t=FakeCredentialedTransport()
        with self.assertRaisesRegex(ValueError,"fake_request_not_exact"):
            t.post(method="POST",path="/posts/"+ID+"/comments",
                   payload={"content":"Hello"},key="real-looking",
                   target=ID)
        self.assertEqual(t.calls,[])

    def test_timeout_and_rejected_response_are_not_success_and_never_retry(self):
        for response in ("timeout","rejected","malformed"):
            with self.subTest(response=response),self.fresh_fixture() as fixture_path:
                result=run_fake_credentialed(fixture_path,response=response)
                self.assertEqual(result.state,"uncertain_simulated")
                self.assertTrue(result.attempted)
                self.assertEqual(result.post_calls,1)
                self.assertFalse(result.dispatch_authorized)
                again=run_fake_credentialed(fixture_path)
                self.assertEqual(again.state,"refused")
                with sqlite3.connect(fixture_path) as con:
                    status=con.execute("SELECT state,attempted_at "
                                       "FROM publish_jobs WHERE run_id=?",(RUN,)).fetchone()
                self.assertEqual(status[0],"uncertain")
                self.assertIsNotNone(status[1])

    def fresh_fixture(self):
        """Simple context manager for independent timeout/challenge cases."""
        from contextlib import contextmanager
        @contextmanager
        def make():
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                source=root/"scout"
                make_saved_scout(source)
                path=root/"r3-unified-fixtures"/"r3-unified-lab.sqlite3"
                fixture(path)
                lab=UnifiedLab(path)
                obs,_=verified_source(source,self.action)
                with sqlite3.connect(path) as con:
                    con.execute("CREATE TABLE bob_friends(handle_key TEXT PRIMARY KEY)")
                lab.propose(self.action,obs,at=NOW)
                lab.queue(self.action,obs,mode="auto",at=NOW,policy=consent_policy())
                d=root/DESCRIPTOR
                d.write_text(json.dumps({
                    "run_id":RUN,"post_id":ID,"reason":self.action.reason,
                    "text":TEXT}),encoding="utf-8")
                os.chmod(d,0o600)
                yield path
        return make()

    def test_challenge_stays_human_only(self):
        result=run_fake_credentialed(self.path,response="challenge")
        self.assertEqual(result.state,"awaiting_verification_simulated")
        self.assertTrue(result.attempted)
        self.assertFalse(result.dispatch_authorized)
        self.assertEqual(self.rows()[0][1],"awaiting_verification_simulated")

    def test_pause_after_claim_blocks_fake_post_and_consumes_attempt(self):
        def pause():
            (self.root/"paused").touch(mode=0o600)
        result=run_fake_credentialed(self.path,after_intent=pause)
        self.assertEqual(result.reason,"barrier_paused_at_dispatch_barrier")
        self.assertEqual(result.post_calls,0)
        self.assertEqual(self.rows()[0][1],"uncertain")
        self.assertIsNotNone(self.rows()[0][2])

    def test_crash_after_fake_post_must_not_retry(self):
        with self.assertRaisesRegex(SimulatedPowerLoss,"synthetic_crash_after_fake_post"):
            run_fake_credentialed(self.path,failpoint="after_post")
        self.assertEqual(self.rows()[0][1],"sending_simulated")
        result=recover_inert_entry(self.path)
        self.assertEqual(result.state,"recovered_simulated")
        self.assertEqual(self.rows()[0][1],"uncertain")
        self.assertEqual(run_fake_credentialed(self.path).state,"refused")

    def test_concurrent_fake_cli_processes_only_one_claim(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.subprocess_cli(),(0,1)))
        self.assertEqual(sum(x.returncode==0 for x in results),1)
        with sqlite3.connect(self.path) as con:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM r3_lab_audit WHERE event='r310_claim'"
            ).fetchone()[0],1)

    def test_no_second_publisher_credentials_or_network_imports_in_adapter(self):
        import bob_r312_adapter as adapter
        import bob_v08.r312_fake_credentialed as fake
        code=inspect.getsource(adapter)+"\n"+inspect.getsource(fake)
        for forbidden in ("urllib.request","HTTPSConnection","subprocess.run(",
                          "systemctl --user", "OPENER.open(", "def api_key("):
            self.assertNotIn(forbidden,code)
        self.assertFalse(candidate_dispatch_is_enabled(None))


if __name__=="__main__":
    unittest.main()
