"""End-to-end synthetic R3 proposal timer ownership / rollback tests.

Systemd is a deterministic fake, files live under a TemporaryDirectory, and
all network/db/credentials/reboot dependencies are absent. No host mutations.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import r3_service_handoff as r3


class FakeSystemd:
    def __init__(self):
        self.states={
            r3.PUBLISHER_TIMER:r3.Snapshot("loaded","active","enabled"),
            r3.PUBLISHER_SERVICE:r3.Snapshot("loaded","inactive","static"),
            r3.SCOUT_TIMER:r3.Snapshot("loaded","active","enabled"),
            r3.SHADOW_TIMER:r3.Snapshot("loaded","active","enabled"),
            r3.SHADOW_SERVICE:r3.Snapshot("loaded","inactive","static"),
            r3.SERVICE:r3.Snapshot("not-found","inactive","not-found"),
            r3.TIMER:r3.Snapshot("not-found","inactive","not-found"),
            r3.COMPETITOR_TIMER:r3.Snapshot("not-found","inactive","not-found"),
            r3.COMPETITOR_SERVICE:r3.Snapshot("not-found","inactive","not-found"),
        }
        self.calls=[]
        self.fail_on=None
        self.interrupt_on=None
        self.prefix=None

    def probe(self,name):
        if name not in r3.EXACT_UNITS:
            raise AssertionError("unreviewed systemd name")
        return self.states[name]

    def control(self,args):
        if any(x in args for x in r3.SENSITIVE):
            raise AssertionError("No publisher or Scout unit is changeable")
        self.calls.append(args)
        if args==self.interrupt_on:
            raise KeyboardInterrupt("synthetic service crash")
        if args==self.fail_on:
            raise ValueError("synthetic systemd failure")
        if args==("daemon-reload",):
            for name in (r3.SERVICE,r3.TIMER):
                exists=(r3.UNITS_DIR/name).is_file()
                self.states[name]=r3.Snapshot(
                    "loaded" if exists else "not-found",
                    self.states[name].active if exists else "inactive",
                    self.states[name].enabled if exists else "not-found")
        elif args==("disable","--now",r3.SHADOW_TIMER):
            self.states[r3.SHADOW_TIMER]=r3.Snapshot(
                "loaded","inactive","disabled")
        elif args==("enable","--now",r3.SHADOW_TIMER):
            self.states[r3.SHADOW_TIMER]=r3.Snapshot(
                "loaded","active","enabled")
        elif args==("disable","--now",r3.TIMER):
            self.states[r3.TIMER]=r3.Snapshot(
                "loaded","inactive","disabled")
        elif args==("enable","--now",r3.TIMER):
            self.states[r3.TIMER]=r3.Snapshot(
                "loaded","active","enabled")
        else:
            raise AssertionError("unexpected systemd action")


class ServiceHandoffTests(unittest.TestCase):
    def setUp(self):
        ctx=tempfile.TemporaryDirectory(prefix="r3-handoff-fixture-")
        self.addCleanup(ctx.cleanup)
        base=Path(ctx.name)
        home=base/"openclaw"
        (home/".config/systemd/user").mkdir(mode=0o700,parents=True)
        (home/".local/state/bob-r3-handoff").mkdir(mode=0o700,parents=True)
        self.root=home
        self.units=home/".config/systemd/user"
        self.state=home/".local/state/bob-r3-handoff"
        self.mock=FakeSystemd()
        self.patches=[
            patch.object(r3,"HOME",home),
            patch.object(r3,"UNITS_DIR",self.units),
            patch.object(r3,"STATE_DIR",self.state),
            patch.object(r3,"JOURNAL",self.state/"journal.json"),
            patch.object(r3,"LOCK",self.state/"lock"),
            patch.object(r3,"_owner",return_value=True),
            patch.object(r3,"_unit_dir_ready",return_value=True),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def apply(self):
        return r3.activate(
            probe=self.mock.probe,control=self.mock.control,
            verified=lambda:True)

    def test_default_preview_never_executes_systemd_or_installs(self):
        info=r3.inspect(probe=self.mock.probe,verified=lambda:False)
        self.assertFalse(info["owner_can_review_handoff"])
        self.assertIn("installed_cutover1_hard_off_unverified",info["blockers"])
        self.assertFalse(info["r3_real_publishing_authorized"])
        self.assertEqual(self.mock.calls,[])
        self.assertEqual(list(self.units.iterdir()),[])
        self.assertFalse(r3.JOURNAL.exists())

    def test_successfully_switches_only_shadow_decision_owner(self):
        self.assertEqual(self.apply(),"proposal_only_timer_active")
        self.assertEqual(self.mock.states[r3.PUBLISHER_TIMER].active,"active")
        self.assertEqual(self.mock.states[r3.SCOUT_TIMER].active,"active")
        self.assertEqual(self.mock.states[r3.SHADOW_TIMER].active,"inactive")
        self.assertEqual(self.mock.states[r3.TIMER].active,"active")
        self.assertEqual(r3._read_journal()["phase"],"complete")
        self.assertEqual(
            {x.name for x in self.units.iterdir()},
            {r3.SERVICE,r3.TIMER})
        self.assertEqual((self.units/r3.TIMER).read_text(),r3.UNIT_TEXT[r3.TIMER])
        self.assertFalse(any(
            r3.PUBLISHER_TIMER in op or r3.PUBLISHER_SERVICE in op
            or r3.SCOUT_TIMER in op for op in self.mock.calls))
        self.assertEqual(r3.recover(
            control=self.mock.control,probe=self.mock.probe,
            verified_owner=lambda:True),
            "shadow_schedule_restored")
        self.assertEqual(self.mock.states[r3.SHADOW_TIMER].active,"active")
        self.assertEqual(self.mock.states[r3.TIMER].active,"inactive")
        self.assertEqual(list(self.units.iterdir()),[])
        self.assertEqual(r3._read_journal()["phase"],"rolled_back")

    def test_r3_timer_enable_failure_rolls_back_unit_files_and_shadow(self):
        self.mock.fail_on=("enable","--now",r3.TIMER)
        self.assertEqual(self.apply(),"rolled_back")
        self.assertEqual(self.mock.states[r3.SHADOW_TIMER].active,"active")
        self.assertEqual(list(self.units.iterdir()),[])
        self.assertEqual(r3._read_journal()["phase"],"rolled_back")
        self.assertEqual(self.mock.states[r3.PUBLISHER_TIMER].active,"active")

    def test_interrupt_after_shadow_timer_disabled_recovers_without_history_loss(self):
        self.mock.interrupt_on=("enable","--now",r3.TIMER)
        with self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertEqual(self.mock.states[r3.SHADOW_TIMER].active,"inactive")
        self.assertEqual(r3._read_journal()["phase"],"shadow_disabled")
        self.mock.interrupt_on=None
        self.assertEqual(r3.recover(
            control=self.mock.control,probe=self.mock.probe,
            verified_owner=lambda:True),
            "shadow_schedule_restored")
        self.assertEqual(self.mock.states[r3.SHADOW_TIMER].active,"active")
        self.assertEqual(self.mock.states[r3.PUBLISHER_TIMER].active,"active")
        self.assertEqual(r3._read_journal()["phase"],"rolled_back")

    def test_drifted_unit_bytes_refuse_recovery_without_overwrite(self):
        self.assertEqual(self.apply(),"proposal_only_timer_active")
        path=self.units/r3.SERVICE
        path.write_text(path.read_text()+"\n# operator change")
        with self.assertRaisesRegex(ValueError,"handoff_unit_changed"):
            r3.recover(control=self.mock.control,probe=self.mock.probe,verified_owner=lambda:True)
        self.assertTrue(path.exists())
        self.assertEqual(r3._read_journal()["phase"],"complete")

    def test_unknown_or_active_competitors_and_busy_shadow_block(self):
        self.mock.states[r3.COMPETITOR_TIMER]=r3.Snapshot(
            "loaded","active","enabled")
        self.assertIn("competing_r3_publisher_unit",
                      r3.assess(self.mock.states))
        with self.assertRaises(ValueError):
            self.apply()
        self.assertFalse(r3.JOURNAL.exists())
        self.mock.states[r3.COMPETITOR_TIMER]=r3.Snapshot(
            "not-found","inactive","not-found")
        self.mock.states[r3.SHADOW_SERVICE]=r3.Snapshot(
            "loaded","active","static")
        self.assertIn("shadow_decision_in_flight",
                      r3.assess(self.mock.states))
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(self.mock.calls,[])

    def test_publisher_or_scout_inactive_blocks_all_changes(self):
        self.mock.states[r3.SCOUT_TIMER]=r3.Snapshot(
            "loaded","inactive","disabled")
        self.assertTrue(r3.assess(self.mock.states))
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(self.mock.calls,[])
        self.assertFalse(r3.JOURNAL.exists())

    def test_installed_hard_off_is_required_before_handoff(self):
        with self.assertRaisesRegex(ValueError,"untrusted_handoff"):
            r3.activate(probe=self.mock.probe,
                        control=self.mock.control,verified=lambda:False)
        self.assertEqual(self.mock.calls,[])
        self.assertEqual(list(self.units.iterdir()),[])

    def test_unknown_journal_and_symlink_unit_fail_closed(self):
        self.assertEqual(self.apply(),"proposal_only_timer_active")
        (self.units/r3.TIMER).unlink()
        (self.units/r3.TIMER).symlink_to(self.units/r3.SERVICE)
        with self.assertRaises(ValueError):
            r3.recover(control=self.mock.control,probe=self.mock.probe,verified_owner=lambda:True)
        self.assertTrue((self.units/r3.TIMER).is_symlink())

    def test_active_proposal_worker_blocks_unit_rollback(self):
        self.assertEqual(self.apply(),"proposal_only_timer_active")
        self.mock.states[r3.SERVICE]=r3.Snapshot("loaded","active","static")
        with self.assertRaisesRegex(ValueError,"r3_proposal_worker_in_flight"):
            r3.recover(control=self.mock.control,probe=self.mock.probe,
                       verified_owner=lambda:True)
        self.assertTrue((self.units/r3.SERVICE).exists())
        self.assertEqual(self.mock.states[r3.TIMER].active,"active")
        self.assertEqual(r3._read_journal()["phase"],"complete")

    def test_symlinked_journal_is_not_read_during_recovery(self):
        self.assertEqual(self.apply(),"proposal_only_timer_active")
        original=r3.JOURNAL.read_bytes()
        reference=self.state/"fake-journal-copy.json"
        reference.write_bytes(original)
        r3.JOURNAL.unlink()
        r3.JOURNAL.symlink_to(reference)
        with self.assertRaisesRegex(ValueError,"handoff_journal_not_private_file"):
            r3.recover(control=self.mock.control,probe=self.mock.probe,
                       verified_owner=lambda:True)
        self.assertEqual(self.mock.states[r3.SHADOW_TIMER].active,"inactive")

    def test_unit_templates_never_create_second_publisher(self):
        r3._validate_template()
        self.assertEqual(set(r3.UNIT_TEXT),{r3.SERVICE,r3.TIMER})
        self.assertNotIn("bob-moltbook-publisher",str(r3.UNIT_TEXT))
        self.assertIn("--once",r3.UNIT_TEXT[r3.SERVICE])
        self.assertIn("Unit="+r3.SERVICE,r3.UNIT_TEXT[r3.TIMER])
        self.assertNotIn("Environment=",str(r3.UNIT_TEXT))
        self.assertEqual(r3.TIMER, "bob-r3-propose.timer")

if __name__=="__main__":
    unittest.main()
