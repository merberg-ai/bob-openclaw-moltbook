"""R4 schedule1 synthetic systemd/SQLite-free lifecycle and hard-Off regression.

Never touches host systemd, a real DB, a Moltbook API, or an OpenClaw model.
All files are under a disposable home and systemctl is an in-memory fake.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src/lib/bob"),str(ROOT/"scripts")]
import bob_r4_schedule as sched


class FakeSystemd:
    def __init__(self):
        def unit(load="loaded",active="inactive",enabled="static",fragment=""):
            return sched.Unit(load,active,enabled,fragment,"")
        self.states={
            sched.SERVICE:unit("not-found","inactive","not-found"),
            sched.TIMER:unit("not-found","inactive","not-found"),
            sched.R3_SERVICE:unit(),
            sched.R3_TIMER:unit(active="active",enabled="enabled"),
            sched.PUBLISHER_SERVICE:unit(),
            sched.PUBLISHER_TIMER:unit(active="active",enabled="enabled"),
            sched.SCOUT_TIMER:unit(active="active",enabled="enabled"),
            sched.SHADOW_SERVICE:unit(),
            sched.SHADOW_TIMER:unit(enabled="disabled"),
        }
        self.calls=[]
        self.fail=None
        self.crash=None
        self.inferences=0

    def probe(self,name):
        if name not in sched.UNITS:
            raise AssertionError("arbitrary systemd unit")
        return self.states[name]

    def change(self,args):
        self.calls.append(args)
        if any(x in args for x in (
            sched.PUBLISHER_TIMER,sched.PUBLISHER_SERVICE,
            sched.SCOUT_TIMER,sched.R3_TIMER,sched.R3_SERVICE,
            sched.SHADOW_TIMER,sched.SHADOW_SERVICE)):
            raise AssertionError("existing worker/scout/publisher must not change")
        if args==self.crash:
            raise KeyboardInterrupt("synthetic power-loss")
        if args==self.fail:
            raise ValueError("synthetic systemctl failure")
        if args==("daemon-reload",):
            for name in (sched.SERVICE,sched.TIMER):
                file=sched.UNIT_DIR/name
                old=self.states[name]
                if file.is_file():
                    self.states[name]=sched.Unit(
                        "loaded",old.active,("static" if name==sched.SERVICE
                                             else old.enabled if old.enabled!="not-found"
                                             else "disabled"),
                        str(file),"")
                else:
                    self.states[name]=sched.Unit("not-found","inactive",
                                                "not-found","","")
        elif args==("enable","--now",sched.TIMER):
            prev=self.states[sched.TIMER]
            self.states[sched.TIMER]=sched.Unit(
                prev.load,"active","enabled",prev.fragment,"")
        elif args==("disable","--now",sched.TIMER):
            prev=self.states[sched.TIMER]
            self.states[sched.TIMER]=sched.Unit(
                prev.load,"inactive","disabled",prev.fragment,"")
        else:
            raise AssertionError("unreviewed command")


@dataclass(frozen=True)
class ValidDecision:
    status:str="skipped"
    reason:str="bob_abstained"
    source_run:str="20261102T105527Z"
    queued:bool=False
    attempted:bool=False
    dispatch_authorized:bool=False


class ScheduleLifecycleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="bob-r4-schedule-fixture-")
        self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)/"openclaw"
        self.unit_dir=self.home/".config/systemd/user"
        self.state=self.home/".local/state/bob-r4-schedule"
        self.unit_dir.mkdir(parents=True,mode=0o700)
        self.fake=FakeSystemd()
        self.mocks=[
            patch.object(sched,"HOME",self.home),
            patch.object(sched,"UNIT_DIR",self.unit_dir),
            patch.object(sched,"STATE",self.state),
            patch.object(sched,"JOURNAL",self.state/"journal.json"),
            patch.object(sched,"LOCK",self.state/"lock"),
            patch.object(sched,"WORK_LOCK",self.state/"worker.lock"),
            patch.object(sched,"_owner",return_value=True),
            patch.object(sched,"_signed",return_value=True),
            patch.object(sched,"_owner_modes_ready",return_value=True),
            patch.object(sched,"_unit_dir_ok",return_value=True),
        ]
        for m in self.mocks:
            m.start()
            self.addCleanup(m.stop)

    def stage(self):
        return sched.stage(probe=self.fake.probe,control=self.fake.change)

    def enable(self):
        return sched.enable(probe=self.fake.probe,control=self.fake.change)

    def disable(self):
        return sched.disable(probe=self.fake.probe,control=self.fake.change)

    def recover(self):
        return sched.recover(probe=self.fake.probe,control=self.fake.change)

    def state_view(self):
        return sched.inspect(probe=self.fake.probe,signed=lambda:True,
                             modes=lambda:True)

    def test_off_first_stage_enable_tick_disable_recover_restaging(self):
        first=self.state_view()
        self.assertEqual(first["phase"],"absent")
        self.assertTrue(first["ready_to_stage"])
        self.assertFalse(first["timer_enabled"])
        self.assertEqual(self.fake.calls,[])
        self.assertEqual(self.stage(),"staged_disabled")
        self.assertEqual(sched._phase(),"staged")
        self.assertFalse(self.state_view()["timer_enabled"])
        self.assertTrue(self.state_view()["ready_to_enable"])
        self.assertEqual(self.fake.calls,[("daemon-reload",)])
        for name in sched.UNIT_TEXT:
            f=self.unit_dir/name
            self.assertEqual(f.read_text(),sched.UNIT_TEXT[name])
            self.assertEqual(stat.S_IMODE(f.stat().st_mode),0o600)
        self.assertEqual(self.enable(),"enabled_private_proposals")
        self.assertTrue(self.state_view()["timer_enabled"])
        self.assertEqual(sched._phase(),"enabled")
        self.assertFalse(any(
            "bob-moltbook-publisher" in str(x) for x in self.fake.calls))
        called=[]
        def worker():
            called.append("one local verified inference")
            return ValidDecision()
        result=sched.once(probe=self.fake.probe,signed=lambda:True,
                          modes=lambda:True,worker=worker)
        self.assertEqual(result["status"],"skipped")
        self.assertEqual(result["reason"],"bob_abstained")
        self.assertEqual(len(called),1)
        self.assertFalse(result["queued"])
        self.assertFalse(result["attempted"])
        self.assertFalse(result["dispatch_authorized"])
        self.assertEqual(self.disable(),"timer_disabled")
        self.assertEqual(sched._phase(),"disabled")
        self.assertFalse(self.state_view()["timer_enabled"])
        self.assertEqual(self.recover(),"schedule_units_removed_no_data_restore")
        self.assertEqual(sched._phase(),"rolled_back")
        self.assertEqual(list(self.unit_dir.iterdir()),[])
        self.assertEqual(self.stage(),"staged_disabled")
        self.assertTrue(self.state_view()["ready_to_enable"])

    def test_no_scheduling_if_r4_paused_or_all_actions_off(self):
        with patch.object(sched,"_owner_modes_ready",return_value=False):
            self.assertFalse(sched.inspect(
                probe=self.fake.probe,signed=lambda:True,
                modes=sched._owner_modes_ready)["ready_to_stage"])
            with self.assertRaisesRegex(ValueError,"owner_modes_not_propose"):
                self.stage()
            self.assertEqual(self.fake.calls,[])
        self.stage()
        self.enable()
        called=[]
        with patch.object(sched,"_owner_modes_ready",return_value=False):
            out=sched.once(probe=self.fake.probe,signed=lambda:True,
                           modes=sched._owner_modes_ready,
                           worker=lambda:called.append("bad"))
        self.assertEqual(out["status"],"none")
        self.assertEqual(called,[])

    def test_untrusted_publisher_state_and_dropins_block_stage(self):
        for name in (sched.PUBLISHER_SERVICE,sched.R3_SERVICE):
            original=self.fake.states[name]
            with self.subTest(name=name):
                self.fake.states[name]=sched.Unit(
                    original.load,"active",original.enabled,
                    original.fragment,original.dropins)
                self.assertFalse(self.state_view()["ready_to_stage"])
                with self.assertRaises(ValueError):
                    self.stage()
                self.fake.states[name]=original
        original=self.fake.states[sched.PUBLISHER_TIMER]
        self.fake.states[sched.PUBLISHER_TIMER]=sched.Unit(
            original.load,original.active,original.enabled,
            original.fragment,"/tmp/unknown-dropin.conf")
        self.assertFalse(self.state_view()["ready_to_stage"])
        with self.assertRaises(ValueError):
            self.stage()
        self.assertEqual(self.fake.calls,[])
        self.assertFalse(self.state.exists())

    def test_collision_and_symlink_fail_closed(self):
        (self.unit_dir/sched.TIMER).write_text("unreviewed timer")
        self.assertFalse(self.state_view()["ready_to_stage"])
        with self.assertRaisesRegex(ValueError,"stage_topology_unverified"):
            self.stage()
        self.assertEqual((self.unit_dir/sched.TIMER).read_text(),
                         "unreviewed timer")
        self.assertEqual(self.fake.calls,[])
        (self.unit_dir/sched.TIMER).unlink()
        (self.unit_dir/sched.TIMER).symlink_to("/tmp/nonexistent-schedule-unit")
        with self.assertRaises(ValueError):
            self.stage()
        self.assertEqual(self.fake.calls,[])

    def test_failed_timer_enable_disables_without_publisher_changes(self):
        self.stage()
        self.fake.fail=("enable","--now",sched.TIMER)
        self.assertEqual(self.enable(),"rolled_back_disabled")
        self.assertEqual(sched._phase(),"disabled")
        self.assertEqual(self.fake.states[sched.TIMER].active,"inactive")
        self.assertNotIn(("disable","--now",sched.PUBLISHER_TIMER),
                         self.fake.calls)

    def test_crash_before_daemon_reload_has_explicit_byte_safe_recovery(self):
        self.fake.crash=("daemon-reload",)
        with self.assertRaises(KeyboardInterrupt):
            self.stage()
        self.assertEqual(sched._phase(),"prepared")
        self.assertEqual({n.name for n in self.unit_dir.iterdir()},
                         set(sched.UNIT_TEXT))
        self.fake.crash=None
        self.assertEqual(self.recover(),"schedule_units_removed_no_data_restore")
        self.assertEqual(sched._phase(),"rolled_back")
        self.assertFalse(any(self.unit_dir.iterdir()))

    def test_tamper_after_stage_refuses_enable_recovery_and_tick(self):
        self.stage()
        target=self.unit_dir/sched.TIMER
        target.write_text(target.read_text()+"\n# malicious edit")
        self.assertFalse(self.state_view()["ready_to_enable"])
        with self.assertRaisesRegex(ValueError,"enable_gate_refused"):
            self.enable()
        with self.assertRaisesRegex(ValueError,"recovery_unit_drift"):
            self.recover()
        self.assertEqual(sched._phase(),"staged")

    def test_drift_during_activation_causes_worker_to_abstain(self):
        self.stage()
        self.enable()
        original=self.fake.states[sched.TIMER]
        self.fake.states[sched.TIMER]=sched.Unit(
            original.load,"inactive","disabled",original.fragment,"")
        called=[]
        out=sched.once(probe=self.fake.probe,signed=lambda:True,
                       modes=lambda:True,worker=lambda:called.append(1))
        self.assertEqual(out["status"],"none")
        self.assertEqual(called,[])
        self.assertFalse(self.state_view()["timer_enabled"])

    def test_invalid_worker_output_never_claims_public_authority(self):
        self.stage()
        self.enable()
        @dataclass(frozen=True)
        class BadDecision:
            status:str="proposed"
            reason:str="bad"
            source_run:str="20261102T105527Z"
            queued:bool=True
            attempted:bool=False
            dispatch_authorized:bool=False
        out=sched.once(probe=self.fake.probe,signed=lambda:True,
                       modes=lambda:True,worker=lambda:BadDecision())
        self.assertEqual(out["status"],"refused")
        for name in ("queued","attempted","dispatch_authorized"):
            self.assertIs(out[name],False)

    def test_operator_cli_no_side_effects_without_interactive_consent(self):
        with patch.object(sched,"inspect",return_value=self.state_view()), \
             patch.object(sched,"stage") as stage, \
             patch.object(sched,"enable") as enable, \
             patch.object(sched.sys,"stdin") as stdin:
            stdin.isatty.return_value=False
            with redirect_stdout(StringIO()):
                self.assertEqual(sched.main(["--stage"]),1)
                self.assertEqual(sched.main(["--enable"]),1)
                self.assertEqual(sched.main(["--check"]),0)
            stage.assert_not_called()
            enable.assert_not_called()
            stdin.isatty.return_value=True
            with patch("builtins.input",return_value="ENABLE EVERYONE"):
                with redirect_stdout(StringIO()):
                    self.assertEqual(sched.main(["--enable"]),1)
            enable.assert_not_called()

    def test_signed_gate_required_for_status_and_worker(self):
        self.stage()
        self.enable()
        called=[]
        result=sched.once(probe=self.fake.probe,signed=lambda:False,
                          modes=lambda:True,worker=lambda:called.append(1))
        self.assertEqual(result["status"],"none")
        self.assertEqual(called,[])
        report=sched.inspect(probe=self.fake.probe,signed=lambda:False,
                             modes=lambda:True)
        self.assertFalse(report["timer_enabled"] and
                         not report["blockers"])


class SourceSafetyTests(unittest.TestCase):
    def test_unit_template_exact_scope_and_no_writer_permissions(self):
        self.assertTrue(sched._template_check())
        self.assertEqual(set(sched.UNIT_TEXT),{sched.SERVICE,sched.TIMER})
        self.assertIn("Persistent=false",sched.UNIT_TEXT[sched.TIMER])
        self.assertIn("OnActiveSec=120min",sched.UNIT_TEXT[sched.TIMER])
        self.assertIn("OnUnitInactiveSec=120min",sched.UNIT_TEXT[sched.TIMER])
        self.assertNotIn("OnCalendar=",sched.UNIT_TEXT[sched.TIMER])
        self.assertNotIn("ExecStartPre=",str(sched.UNIT_TEXT))
        self.assertNotIn("moltbook.com",str(sched.UNIT_TEXT))
        self.assertNotIn("bob-moltbook-publisher",str(sched.UNIT_TEXT))

    def test_hardcoded_systemd_commands_only(self):
        for forbidden in (
            "os.system(", "shell=True", "Popen(", "requests.post(",
            "api_key(", "set_mode(", "set_pause(",
            "db.commit(", "UPDATE publish", "INSERT INTO publish_jobs",
            "systemctl --user stop bob-moltbook-publisher",
        ):
            self.assertNotIn(forbidden,(ROOT/"src/lib/bob/bob_r4_schedule.py").read_text())
        self.assertIn("('disable','--now',TIMER)",(ROOT/"src/lib/bob/bob_r4_schedule.py").read_text().replace('"',"'"))


if __name__=="__main__":
    unittest.main()
