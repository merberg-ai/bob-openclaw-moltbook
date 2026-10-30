"""OC4.1 diagnostic polish: timestamp truth, verified handoff subset, timer fallback.

Synthetic only: no live user services, no web actions and no publication.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import json
import sys
import tempfile
import sqlite3
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
sys.path.insert(0,str(ROOT/"tests"))

import bob_inactivity as oc4
import bob_operations_diagnostics as operations
from test_oc4_inactivity import fixture, observed, RID1, RID2, RID3, NOW


class TimerFallbackTests(unittest.TestCase):
    def test_no_realtime_uses_systemd_exact_timer_json(self):
        calls=[]
        class Result:
            def __init__(self, stdout,code=0):
                self.stdout=stdout
                self.returncode=code
        def run(args,**kw):
            calls.append(args)
            self.assertNotIn("shell",kw)
            self.assertEqual(kw["timeout"],1.5)
            if "show" in args:
                return Result("n/a")
            unit=args[-1]
            return Result(json.dumps([{"unit":unit,"next":"Fri 2026-10-30 16:40:00 UTC"}]))
        result=operations._timer_schedules(run=run)
        self.assertEqual(set(result),{"publisher","scout"})
        self.assertEqual(result["publisher"],"Fri 2026-10-30 16:40:00 UTC")
        self.assertEqual(len(calls),4)
        self.assertEqual(set(args[-1] for args in calls if "list-timers" in args),
                         set(operations.TIMERS.values()))
        self.assertTrue(all(args[:2]==["systemctl","--user"] for args in calls))

    def test_realtime_does_not_require_fallback(self):
        calls=[]
        class Result:
            returncode=0
            stdout="Fri 2026-10-30 16:40:00 UTC"
        def run(args,**kw):
            calls.append(args)
            return Result()
        self.assertEqual(len(operations._timer_schedules(run=run)),2)
        self.assertTrue(all("show" in args for args in calls))

    def test_invalid_wrong_unit_or_command_failure_not_a_schedule(self):
        class Result:
            returncode=0
            def __init__(self,stdout):self.stdout=stdout
        cases=['not-json','[{"unit":"attacker.timer","next":"Tomorrow"}]',
               '[{"unit":"bob-moltbook-scout.timer","next":"<script>"}]',
               '[{"unit":"bob-moltbook-scout.timer","next":"n/a"}]']
        for body in cases:
            with self.subTest(body=body[:18]):
                def run(args,**kw):
                    return Result("n/a" if "show" in args else body)
                result=operations._timer_schedules(run=run)
                self.assertEqual(result["scout"],"")
                self.assertEqual(result["publisher"],"")

    def test_microseconds_only_if_plausible(self):
        class Result:
            returncode=0
            def __init__(self,stdout):self.stdout=stdout
        def run(args,**kw):
            payload=[{"unit":args[-1],"next":1793378400000000}]
            return Result("n/a" if "show" in args else json.dumps(payload))
        result=operations._timer_schedules(run=run)
        self.assertIn("2026",result["publisher"])


class HistoryPolishTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"activity.sqlite3"
        fixture(self.path)

    def test_history_window_and_real_block_timestamps(self):
        with patch.object(oc4,"manual_recovery_allowed",return_value=True) as checked:
            history=oc4.read_private(self.path,at=NOW)
        self.assertEqual(history["approved_blocked"],1)
        self.assertEqual(history["manual_handoff"]["verified"],1)
        self.assertEqual(history["manual_handoff"]["checked"],1)
        self.assertEqual(history["manual_handoff"]["run_ids"],[RID1])
        self.assertEqual(history["job_window"]["inspected"],4)
        self.assertEqual(history["job_window"]["oldest"],"2026-10-30T16:15:00+00:00")
        self.assertEqual(history["latest_review_block"]["approved"],"2026-10-30T16:15:00+00:00")
        self.assertEqual(checked.call_count,1)
        result=oc4.explain(observed(),history,at=NOW)
        auto=next(x for x in result["sections"] if x["key"]=="auto")
        self.assertIn("history 2026-10-30 to 2026-10-30 UTC",auto["summary"])
        approved=next(r for r in auto["reasons"] if r["code"]=="AUTO_APPROVED_HANDOFF")
        self.assertIn("1 of 1 inspected",approved["detail"])
        self.assertEqual(approved["source"],"2026-10-30T16:15:00+00:00")
        self.assertEqual(result["handoff_links"],[RID1])
        markup=oc4.page(lambda title,body,route:body,data=result)
        self.assertIn("/scout#run-"+RID1,markup)
        self.assertNotIn("Time unavailable",markup)
        self.assertIn("Most recent Scout checkpoint",markup)
        self.assertIn("Last publisher evaluation",markup)
        self.assertIn("Not reported by systemd",markup.replace(
            "Fri 2026-10-30 16:40:00 UTC","Not reported by systemd"))

    def test_no_verification_means_no_actionable_links(self):
        with patch.object(oc4,"manual_recovery_allowed",return_value=False):
            history=oc4.read_private(self.path,at=NOW)
        result=oc4.explain(observed(),history,at=NOW)
        self.assertEqual(result["handoff_verified"],0)
        self.assertEqual(result["handoff_links"],[])
        html=oc4.page(lambda a,b,c:b,data=result)
        self.assertNotIn("/scout#run-",html)
        self.assertIn("historical approved auto",html)

    def test_failed_source_check_is_not_a_verified_handoff(self):
        with patch.object(oc4,"manual_recovery_allowed",side_effect=OSError()):
            history=oc4.read_private(self.path,at=NOW)
        self.assertEqual(history["manual_handoff"]["verified"],0)
        self.assertTrue(history["available"])

    def test_challenge_or_attempt_never_reaches_verification(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE publish_jobs SET challenge_code='challenge' WHERE run_id=?",
                       (RID1,))
        with patch.object(oc4,"manual_recovery_allowed",side_effect=AssertionError(
                 "Must never validate a challenged job")):
            history=oc4.read_private(self.path,at=NOW)
        self.assertEqual(history["approved_blocked"],0)

    def test_blank_source_label_is_not_fake_timestamp(self):
        self.assertEqual(oc4._source(""),"Policy / historical summary")
        self.assertEqual(oc4._source("2026-10-30T14:00:00Z"),
                         "2026-10-30T14:00:00+00:00")

if __name__=="__main__":
    unittest.main()
