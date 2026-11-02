"""R4 schedule1 signed source and isolated six-file transactional rehearsal.

No real systemd, host, credentials, OpenClaw, or Moltbook API used. Checks
the actual candidate payload bytes and updater's code-only rollback paths.
"""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import report_r4_schedule_candidate as audit

NEW="v0.8.0-r4schedule1"
OLD="v0.8.0-r4format1"
OLD_EXISTING=frozenset((
    "bob-release-updater","bobctl","bob_r4_installed_gate.py",
    "bob_r4_web.py",
))


def signed_old_host():
    return {
        "release":OLD,"signed_installed_source":True,
        "legacy_and_r3_registry":True,"authenticated_https":True,
        "new_r4_routes":True,"versioned_additive_schema":True,
        "publisher_inactive_at_check":True,"new_r4_actions_attempted":0,
    }


class ScheduleSourceTests(unittest.TestCase):
    def test_exact_offer_is_six_signed_files_with_no_auto_schedule(self):
        result=audit.inspect()
        self.assertEqual(result["candidate_release"],NEW)
        self.assertEqual(result["from_release"],OLD)
        self.assertEqual(result["signed_candidate_files"],6)
        self.assertEqual(set(result["verified_sha256"]),set(audit.ALLOWED))
        self.assertTrue(result["exact_promoted_candidate"])
        for name in ("unit_stage_owner_confirmed_only",
                     "schedule_enable_owner_confirmed_only",
                     "existing_r3_publisher_and_scout_unchanged",
                     "all_r4_public_sends_hard_off","no_automatic_model_retry",
                     "authenticated_https"):
            self.assertIs(result[name],True)
        for name in ("schedule_installed_by_updater",
                     "schedule_enabled_by_updater",
                     "no_database_migration",
                     "host_installed_by_source_audit"):
            if name=="no_database_migration":
                self.assertIs(result[name],True)
            else:
                self.assertIs(result[name],False)
        self.assertEqual(updater.manager_transport(NEW),"https")
        offer=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(offer,json.loads((ROOT/
            "releases/candidates/r4-schedule1-offfirst.json").read_text()))
        self.assertEqual(offer["from"],OLD)
        self.assertEqual({x["name"]:x["source"] for x in offer["files"]},
                         audit.ALLOWED)

    def test_host_preflight_requires_signed_format1_and_idle_publisher(self):
        for name,wrong in (
            ("release","v0.8.0-r4propose1"),
            ("signed_installed_source",False),
            ("legacy_and_r3_registry",False),
            ("authenticated_https",False),
            ("new_r4_routes",False),
            ("versioned_additive_schema",False),
            ("publisher_inactive_at_check",False),
            ("new_r4_actions_attempted",1),
        ):
            with self.subTest(name=name), \
                 patch("report_r4_installed.inspect",
                       return_value={**signed_old_host(),name:wrong}), \
                 patch.object(updater,"r4_publisher_inactive",return_value=True):
                self.assertFalse(updater.preflight_r4_schedule_patch())
        with patch("report_r4_installed.inspect",
                   return_value=signed_old_host()), \
             patch.object(updater,"r4_publisher_inactive",return_value=True):
            self.assertTrue(updater.preflight_r4_schedule_patch())
        with patch("report_r4_installed.inspect",
                   return_value=signed_old_host()), \
             patch.object(updater,"r4_publisher_inactive",return_value=False):
            self.assertFalse(updater.preflight_r4_schedule_patch())

    def test_source_audit_cannot_install_or_mutate_live_host(self):
        self.assertEqual(audit.main(["--install"]),2)
        self.assertEqual(audit.main(["--check"]),0)
        text=(ROOT/"scripts/report_r4_schedule_candidate.py").read_text()
        for forbidden in ("subprocess.run(", "sqlite3.connect(", "systemctl ",
                          "api_key(", "openclaw_decide(", "set_mode(",
                          "set_pause(", "requests.post(", "updater.update("):
            self.assertNotIn(forbidden,text)


class SignedUpdaterRehearsal(unittest.TestCase):
    def setUp(self):
        fixture=tempfile.TemporaryDirectory(prefix="r4-schedule1-signed-")
        self.addCleanup(fixture.cleanup)
        home=Path(fixture.name)
        self.bin=home/".local/bin"
        self.state=home/".local/state/bob-updater"
        self.db=home/".config/moltbook/activity-queue.sqlite3"
        self.backups=home/".local/state/bob-baseline/backups"
        for folder in (self.bin,self.state,self.db.parent):
            folder.mkdir(parents=True,mode=0o700)
        with sqlite3.connect(self.db) as db:
            db.execute("CREATE TABLE receipts (source TEXT)")
            db.execute("INSERT INTO receipts VALUES ('historical R3 and R4 state')")
        self.db.chmod(0o600)
        self.offer=json.loads((ROOT/"releases/current.json").read_text())
        self.payloads={x["name"]:updater.release_bytes(ROOT,x)
                       for x in self.offer["files"]}
        self.old_bytes={}
        for name in OLD_EXISTING:
            data=("#!/usr/bin/env python3\n# fake hash-verified previous "+
                  name+"\n").encode()
            self.old_bytes[name]=data
            p=self.bin/name
            p.write_bytes(data)
            p.chmod(0o600)
        self.installed={"format":updater.FORMAT,"release":OLD,
                        "files":{name:hashlib.sha256(raw).hexdigest()
                                 for name,raw in self.old_bytes.items()}}
        self.registry=self.state/"installed.json"
        self.journal=self.state/"transaction.json"
        self.registry.write_text(json.dumps(self.installed))
        self.registry.chmod(0o600)
        self.journal.write_text(json.dumps({
            "format":updater.FORMAT,"release":OLD,
            "phase":"complete","restart_manager":True}))
        self.journal.chmod(0o600)

    def _isolated(self,stack):
        for key,path in (
            ("BIN",self.bin),("STATE_DIR",self.state),
            ("LOCK",self.state/"lock"),
            ("REGISTRY",self.registry),("JOURNAL",self.journal),
            ("DB",self.db),("BACKUP_DIR",self.backups),
            ("HOME",self.bin.parent.parent),
        ):
            stack.enter_context(patch.object(updater,key,path))
        stack.enter_context(patch.object(updater,"r4_publisher_inactive",
                                         return_value=True))
        stack.enter_context(patch.object(updater,"healthy",return_value=True))
        restart=stack.enter_context(patch.object(updater,"restart_manager"))
        stack.enter_context(patch.object(updater,"wait_for_health",
                                         return_value=True))
        backup=stack.enter_context(patch(
            "backup_live_sqlite.create_verified_backup",
            return_value={"restore_rehearsal":"passed"}))
        return restart,backup

    def _ledger(self):
        with sqlite3.connect(self.db) as db:
            return db.execute("SELECT source FROM receipts").fetchone()[0]

    def test_real_payload_install_then_code_only_owner_rollback(self):
        with ExitStack() as stack:
            restart,backup=self._isolated(stack)
            self.assertEqual(updater.update(
                ROOT,self.installed,self.offer,self.payloads,
                auth="Basic test-only"),"updated")
            self.assertEqual(updater.registry()["release"],NEW)
            self.assertTrue(updater.live_ok(updater.registry()))
            self.assertEqual(updater.read_journal()["phase"],"complete")
            self.assertEqual(restart.call_count,1)
            backup.assert_called_once()
            self.assertEqual(self._ledger(),"historical R3 and R4 state")
            for name,payload in self.payloads.items():
                self.assertEqual((self.bin/name).read_bytes(),payload)
            self.assertTrue((self.bin/"bob-r4-schedule").exists())
            self.assertTrue((self.bin/"bob_r4_schedule.py").exists())
            # Existing unit files are *not* installed by the updater.
            self.assertFalse((self.bin.parent.parent/
                ".config/systemd/user/bob-r4-propose.timer").exists())
            self.assertEqual(updater.rollback_completed_r4(
                auth="Basic test-only"),"baseline_restored")
            self.assertEqual(updater.registry()["release"],OLD)
            self.assertEqual(updater.read_journal()["phase"],"rolled_back")
            self.assertEqual(restart.call_count,2)
            self.assertEqual(self._ledger(),"historical R3 and R4 state")
            for name,raw in self.old_bytes.items():
                self.assertEqual((self.bin/name).read_bytes(),raw)
            self.assertFalse((self.bin/"bob-r4-schedule").exists())
            self.assertFalse((self.bin/"bob_r4_schedule.py").exists())

    def test_authenticated_https_postflight_failure_rolls_back_code(self):
        with ExitStack() as stack:
            restart,_=self._isolated(stack)
            stack.enter_context(patch.object(
                updater,"wait_for_health",
                side_effect=lambda auth,release=None: release==OLD))
            self.assertEqual(updater.update(
                ROOT,self.installed,self.offer,self.payloads,
                auth="Basic test-only"),"rolled_back")
            self.assertEqual(updater.registry()["release"],OLD)
            self.assertEqual(updater.read_journal()["phase"],"rolled_back")
            self.assertEqual(restart.call_count,2)
            self.assertEqual(self._ledger(),"historical R3 and R4 state")
            self.assertFalse((self.bin/"bob-r4-schedule").exists())
            self.assertFalse((self.bin/"bob_r4_schedule.py").exists())

    def test_owner_rollback_refuses_when_schedule_units_exist(self):
        with ExitStack() as stack:
            self._isolated(stack)
            self.assertEqual(updater.update(
                ROOT,self.installed,self.offer,self.payloads,
                auth="Basic test-only"),"updated")
            folder=self.bin.parent.parent/".config/systemd/user"
            folder.mkdir(parents=True,mode=0o700)
            file=folder/"bob-r4-propose.timer"
            file.write_text("synthetic staged operator timer")
            self.assertFalse(updater.r4_schedule_units_absent())
            with self.assertRaisesRegex(
                    ValueError,"r4_schedule_units_must_be_recovered_first"):
                updater.rollback_completed_r4(auth="Basic test-only")
            self.assertEqual(updater.registry()["release"],NEW)
            self.assertEqual(self._ledger(),"historical R3 and R4 state")


if __name__=="__main__":
    unittest.main()
