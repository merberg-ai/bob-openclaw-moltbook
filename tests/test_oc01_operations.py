"""OC0/OC1 offline fixtures: genuine vs stale work, policy time vs timers,
manual backlog and original authoring, and read-only Overview rendering."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"webui"))
import bob_operations_diagnostics as ops
import bob_overview as overview

NOW=datetime(2026,10,30,13,0,tzinfo=timezone.utc)

def metrics(manual=6,auto=0,originals=0,requests=0,drafts=0,used=2):
    return dict(available=True,auto_enabled=True,
        usage=dict(comments=used,auto=0,originals=0),
        limits=dict(comment_daily=10,comment_auto_daily=6,original_daily=4),
        queues=dict(comments_queued=manual+auto,manual_queued=manual,
                    auto_queued=auto,originals_queued=originals,
                    originals_draft=drafts,generation_queued=requests),
        next_possible_utc=dict(comments="2026-10-30T13:35:00+00:00",
                               originals="2026-10-30T13:00:00+00:00"))

def services():
    return [{"name":"Scout timer","state":"running"},
            {"name":"Publisher timer","state":"running"},
            {"name":"Gateway","state":"running"},
            {"name":"Gateway port","state":"listening"},
            {"name":"Ollama","state":"ready"}]

def checkpoint(worker,stage,*,minutes_ago=0):
    return dict(worker=worker,stage=stage,stale=False,job_id="20261030T130000Z",
                updated_at=(NOW-timedelta(minutes=minutes_ago)).isoformat())

class OperationsTests(unittest.TestCase):
    def test_screenshot_fixture_describes_attempts_and_no_guessed_inactivity_cause(self):
        result=ops.explain(metrics(),services(),[],False,at=NOW,timers={
            "scout":"Fri 2026-10-30 13:15:00 UTC",
            "publisher":"Fri 2026-10-30 13:20:00 UTC"})
        self.assertEqual(result["state"],"waiting")
        self.assertEqual(result["lanes"][1]["code"],"RATE_LIMIT")
        self.assertIn("6 queued comments",result["lanes"][1]["reason"])
        self.assertIn("6 manual queued first",result["lanes"][1]["reason"])
        self.assertIn("not a scheduled timer run",result["lanes"][1]["reason"])
        self.assertIn("owner-requested",result["lanes"][2]["activity"])
        self.assertEqual(result["lanes"][2]["code"],"MANUAL_ONLY")
        self.assertEqual(result["lanes"][1]["next_scheduled"],
                         "Fri 2026-10-30 13:20:00 UTC")
        self.assertNotIn("13:35:00 UTC",result["lanes"][1]["next_scheduled"])
        self.assertNotIn("publishing now",result["headline"])
        self.assertEqual(result["lanes"][3]["code"],"DEPENDENCIES_READY")

    def test_checkpoint_active_not_stale_or_future(self):
        result=ops.explain(metrics(),services(),[checkpoint("scout","generating")],
                           False,at=NOW,timers={})
        self.assertEqual(result["state"],"active")
        self.assertEqual(result["lanes"][0]["activity"],
                         "Thinking through a request with the local agent")
        stale=ops.explain(metrics(),services(),[checkpoint("scout","generating",minutes_ago=10)],
                          False,at=NOW,timers={})
        self.assertNotEqual(stale["state"],"active")
        self.assertNotEqual(stale["lanes"][0]["state"],"active")
        future=checkpoint("scout","generating")
        future["updated_at"]=(NOW+timedelta(minutes=2)).isoformat()
        self.assertNotEqual(ops.explain(metrics(),services(),[future],False,at=NOW,timers={})["state"],"active")

    def test_global_pause_and_inactive_timers_not_confused_with_healthy_idle(self):
        paused=ops.explain(metrics(),services(),[],True,at=NOW,timers={})
        self.assertEqual(paused["lanes"][0]["code"],"GLOBAL_PAUSE")
        self.assertEqual(paused["lanes"][1]["code"],"GLOBAL_PAUSE")
        broken=[{"name":"Scout timer","state":"inactive"},
                {"name":"Publisher timer","state":"failed"}]
        down=ops.explain(metrics(),broken,[],False,at=NOW,timers={})
        self.assertEqual(down["lanes"][0]["code"],"TIMER_DOWN")
        self.assertEqual(down["lanes"][1]["code"],"TIMER_DOWN")
        self.assertEqual(down["state"],"blocked")

    def test_no_auto_candidate_unknown_and_original_drafts_owner_action(self):
        no=metrics(manual=0,auto=0,drafts=0)
        no["next_possible_utc"]["comments"]=NOW.isoformat()
        value=ops.explain(no,services(),[],False,at=NOW,timers={})
        self.assertEqual(value["lanes"][1]["code"],"NO_QUEUE")
        self.assertIn("eligible Scout selection has not been confirmed",value["lanes"][1]["reason"])
        self.assertNotIn("Scout has failed",value["lanes"][1]["reason"])
        no["auto_enabled"]=False
        self.assertEqual(ops.explain(no,services(),[],False,at=NOW,timers={})["lanes"][1]["code"],
                         "AUTO_DISABLED")
        no["queues"]["originals_draft"]=1
        self.assertEqual(ops.explain(no,services(),[],False,at=NOW,timers={})["lanes"][2]["code"],
                         "OWNER_ACTION")
        no["queues"]["originals_draft"]=0
        no["queues"]["generation_queued"]=1
        self.assertEqual(ops.explain(no,services(),[],False,at=NOW,timers={})["lanes"][2]["code"],
                         "DRAFT_REQUEST_WAITING")
        no["queues"]["generation_queued"]=0
        no["queues"]["originals_queued"]=1
        self.assertIn(ops.explain(no,services(),[],False,at=NOW,timers={})["lanes"][2]["code"],
                      ("RATE_LIMIT","WAITING_WORKER"))

    def test_missing_metrics_and_missing_dependency_are_truthful(self):
        result=ops.explain({"available":False},[],[],False,at=NOW,timers={})
        self.assertEqual(result["lanes"][1]["code"],"NO_METRICS")
        self.assertEqual(result["lanes"][2]["code"],"NO_METRICS")
        self.assertEqual(result["lanes"][3]["code"],"DEPENDENCY_UNKNOWN")
        offline=ops.explain(metrics(),[{"name":"Ollama","state":"unavailable"},
                                        {"name":"Gateway","state":"running"}],[],
                            False,at=NOW,timers={})
        self.assertEqual(offline["lanes"][3]["code"],"DEPENDENCY_DOWN")

    def test_allowlisted_systemd_observer_no_shell_or_user_unit_names(self):
        calls=[]
        class Result:
            stdout="Fri 2026-10-30 13:20:00 UTC\n"
            returncode=0
        def reader(args,**kw):
            calls.append((args,kw))
            return Result()
        result=ops._timer_schedules(run=reader)
        self.assertEqual(set(result),{"scout","publisher"})
        self.assertEqual(len(calls),2)
        self.assertTrue(all(args[:3]==["systemctl","--user","show"] for args,_ in calls))
        self.assertTrue(all(args[3] in ops.TIMERS.values() for args,_ in calls))
        self.assertTrue(all(kwargs["check"] is False and kwargs["timeout"]==1.5 for _,kwargs in calls))
        self.assertNotIn("shell",calls[0][1])
        self.assertNotIn("api_key",str(calls))

    def test_bad_timer_output_fails_closed_and_missing_reader_does_not_crash(self):
        class Result:
            stdout="<script>alert(1)</script>"
            returncode=0
        self.assertEqual(ops._timer_schedules(run=lambda *a,**kw:Result()),
                         {"scout":"","publisher":""})
        result=ops.collect(metrics(),services(),[],False,at=NOW,
                           timer_reader=lambda: (_ for _ in ()).throw(OSError()))
        self.assertEqual(result["lanes"][0]["next_scheduled"],"")

    def test_html_safely_renders_live_card_between_gauges_and_queue(self):
        source=ops.explain(metrics(),services(),[],False,at=NOW,timers={})
        source["detail"]='<img src=x onerror="alert(1)">'
        source["lanes"][0]["reason"]='<script>alert("bad")</script>'
        data=dict(operations=source,metrics={"available":False},services=[],workers=[],
                  queues_observed=False,jobs=[])
        with patch.object(overview,"wrap",side_effect=lambda title,html,path:
                          "<html><head></head><body>"+html+"</body></html>"):
            html=overview.page(data)
        self.assertIn('<section class="bo-panel bo-now"',html)
        self.assertLess(html.index("Daily activity budgets"),html.index("Bob right now"))
        self.assertLess(html.index("Bob right now"),html.index("Queue &amp; publication"))
        self.assertIn('&lt;script&gt;alert(&quot;bad&quot;)&lt;/script&gt;',html)
        self.assertNotIn('<script>alert(',html)
        self.assertNotIn('<img src=x onerror=',html)
        self.assertIn('Earliest policy-permitted comment (not scheduled)',html)
        self.assertIn('id="bo-now-lanes"',html)
        self.assertIn('src="/assets/bob-overview.js"',html)

    def test_refresh_uses_textcontent_not_html_or_new_permissions(self):
        js=overview.javascript()
        self.assertIn('const ops=d.operations',js)
        self.assertIn('current.replaceChildren()',js)
        self.assertIn('activity.textContent=',js)
        self.assertIn("setInterval(refresh,15000)",js)
        self.assertIn("document.hidden",js)
        self.assertNotIn("innerHTML",js)
        self.assertNotIn("fetch('/api/",js.replace("fetch('/api/dashboard/overview'",""))
        self.assertNotIn("method:'POST'",js)
        self.assertIn("@media(prefers-reduced-motion:reduce)",overview.STYLE)


if __name__=="__main__":
    unittest.main()
