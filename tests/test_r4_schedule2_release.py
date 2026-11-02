"""R4 schedule2: byte-exact R3 first-tick dropin and code-only signed patch.

All updater, service, filesystem and SQLite fixtures are synthetic. No real
Moltbook, model calls, WSL systemd commands, credentials, or host writes.
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
import report_r4_schedule2_candidate as audit
import bob_r4_schedule as schedule
import repair_r3_first_timer as original

NEW="v0.8.0-r4schedule2"
OLD="v0.8.0-r4schedule1"


def prior_acceptance():
    return {"release":OLD,"acceptance":"PASS",
            "signed_installed_source":True,
            "legacy_and_r3_registry":True,
            "authenticated_https":True,
            "new_r4_routes":True,
            "versioned_additive_schema":True,
            "publisher_inactive_at_check":True,
            "new_r4_actions_attempted":0}


class ExactScopeTests(unittest.TestCase):
    def test_pinned_r3_bootstrap_matches_previously_reviewed_repair(self):
        self.assertEqual(schedule.R3_BOOTSTRAP_BYTES,original.BODY)
        self.assertEqual(schedule.R3_BOOTSTRAP.name,"10-first-run.conf")
        self.assertEqual(schedule.R3_BOOTSTRAP.parent.name,
                         schedule.R3_TIMER+".d")
        self.assertIn("OnUnitInactiveSec=35min",
                      (ROOT/"scripts/r3_service_handoff.py").read_text())
        self.assertEqual(schedule.RELEASE,NEW)
        self.assertEqual(updater.manager_transport(NEW),"https")
        report=audit.inspect()
        self.assertEqual(report["candidate_release"],NEW)
        self.assertEqual(report["from_release"],OLD)
        self.assertEqual(report["signed_candidate_files"],4)
        self.assertTrue(report["unreviewed_dropins_still_refused"])
        self.assertTrue(report["public_r4_sends_hard_off"])
        self.assertFalse(report["schedule_install_or_activation_by_updater"])
        self.assertFalse(report["database_migration"])

    def test_signed_schedule2_refuses_unaccepted_predecessor_or_staged_units(self):
        for field,bad in (
            ("release","v0.8.0-r4format1"),
            ("signed_installed_source",False),
            ("legacy_and_r3_registry",False),
            ("authenticated_https",False),
            ("new_r4_routes",False),
            ("versioned_additive_schema",False),
            ("publisher_inactive_at_check",False),
            ("new_r4_actions_attempted",1),
        ):
            with self.subTest(field=field), \
                 patch("report_r4_installed.inspect",
                       return_value={**prior_acceptance(),field:bad}), \
                 patch.object(updater,"r4_publisher_inactive",return_value=True), \
                 patch.object(updater,"r4_schedule_units_absent",return_value=True):
                self.assertFalse(updater.preflight_r4_schedule2_patch())
        with patch("report_r4_installed.inspect",
                   return_value=prior_acceptance()), \
             patch.object(updater,"r4_publisher_inactive",return_value=True), \
             patch.object(updater,"r4_schedule_units_absent",return_value=False):
            self.assertFalse(updater.preflight_r4_schedule2_patch())
        with patch("report_r4_installed.inspect",
                   return_value=prior_acceptance()), \
             patch.object(updater,"r4_publisher_inactive",return_value=True), \
             patch.object(updater,"r4_schedule_units_absent",return_value=True):
            self.assertTrue(updater.preflight_r4_schedule2_patch())

    def test_source_audit_only_reads(self):
        self.assertEqual(audit.main(["--check"]),0)
        self.assertEqual(audit.main(["--apply"]),2)
        s=(ROOT/"scripts/report_r4_schedule2_candidate.py").read_text()
        for forbidden in ("subprocess.run(", "sqlite3.connect(",
                          "requests.post(", "openclaw_decide(", "set_mode(",
                          "set_pause(", "updater.update(", "os.system("):
            self.assertNotIn(forbidden,s)


class IsolatedSignedUpdateTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r4-schedule2-patch-")
        self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)
        self.bin=self.home/".local/bin"
        self.state=self.home/".local/state/bob-updater"
        self.db=self.home/".config/moltbook/activity-queue.sqlite3"
        self.backups=self.home/".local/state/bob-baseline/backups"
        for d in (self.bin,self.state,self.db.parent):
            d.mkdir(parents=True,mode=0o700)
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE protected (value TEXT)")
            conn.execute("INSERT INTO protected VALUES ('R3 and R4 history unchanged')")
        self.db.chmod(0o600)
        self.offer=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(self.offer["release"],NEW)
        self.payloads={x["name"]:updater.release_bytes(ROOT,x)
                       for x in self.offer["files"]}
        self.old_bytes={}
        for name in self.payloads:
            data=("#!/usr/bin/env python3\n# synthetic schedule1 "+name+"\n").encode()
            self.old_bytes[name]=data
            f=self.bin/name
            f.write_bytes(data)
            f.chmod(0o600)
        self.installed={"format":updater.FORMAT,"release":OLD,
                        "files":{name:hashlib.sha256(data).hexdigest()
                                 for name,data in self.old_bytes.items()}}
        (self.state/"installed.json").write_text(json.dumps(self.installed))
        (self.state/"installed.json").chmod(0o600)
        (self.state/"transaction.json").write_text(json.dumps({
            "format":updater.FORMAT,"release":OLD,
            "phase":"complete","restart_manager":True}))
        (self.state/"transaction.json").chmod(0o600)

    def context(self,stack):
        for key,path in (
            ("HOME",self.home),("BIN",self.bin),
            ("STATE_DIR",self.state),("LOCK",self.state/"lock"),
            ("REGISTRY",self.state/"installed.json"),
            ("JOURNAL",self.state/"transaction.json"),
            ("DB",self.db),("BACKUP_DIR",self.backups),
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

    def history(self):
        with sqlite3.connect(self.db) as conn:
            return conn.execute("SELECT value FROM protected").fetchone()[0]

    def test_signed_four_file_install_and_code_only_rollback(self):
        with ExitStack() as stack:
            restarted,backup=self.context(stack)
            self.assertEqual(updater.update(
                ROOT,self.installed,self.offer,self.payloads,
                auth="Basic synthetic-test"),"updated")
            self.assertEqual(updater.registry()["release"],NEW)
            self.assertTrue(updater.live_ok(updater.registry()))
            self.assertEqual(updater.read_journal()["phase"],"complete")
            backup.assert_called_once()
            self.assertEqual(restarted.call_count,1)
            self.assertEqual(self.history(),"R3 and R4 history unchanged")
            for name,payload in self.payloads.items():
                self.assertEqual((self.bin/name).read_bytes(),payload)
            self.assertEqual(updater.rollback_completed_r4(
                auth="Basic synthetic-test"),"baseline_restored")
            self.assertEqual(updater.registry()["release"],OLD)
            self.assertEqual(restarted.call_count,2)
            self.assertEqual(self.history(),"R3 and R4 history unchanged")
            for name,payload in self.old_bytes.items():
                self.assertEqual((self.bin/name).read_bytes(),payload)

    def test_https_postflight_failure_rolls_back_exact_old_code(self):
        with ExitStack() as stack:
            restarted,_=self.context(stack)
            stack.enter_context(patch.object(
                updater,"wait_for_health",
                side_effect=lambda auth,release=None:release==OLD))
            self.assertEqual(updater.update(
                ROOT,self.installed,self.offer,self.payloads,
                auth="Basic synthetic-test"),"rolled_back")
            self.assertEqual(updater.registry()["release"],OLD)
            self.assertEqual(self.history(),"R3 and R4 history unchanged")
            self.assertEqual(restarted.call_count,2)
            for name,data in self.old_bytes.items():
                self.assertEqual((self.bin/name).read_bytes(),data)

    def test_install_and_rollback_refuse_owner_staged_r4_timer(self):
        with ExitStack() as stack:
            self.context(stack)
            folder=self.home/".config/systemd/user"
            folder.mkdir(parents=True,mode=0o700)
            timer=folder/"bob-r4-propose.timer"
            timer.write_text("synthetic incompatible unit")
            with self.assertRaisesRegex(ValueError,"r4_schedule2_units_must_be_absent"):
                updater.update(ROOT,self.installed,self.offer,self.payloads,
                               auth="Basic synthetic-test")
            self.assertEqual(updater.registry()["release"],OLD)
            timer.unlink()
            self.assertEqual(updater.update(
                ROOT,self.installed,self.offer,self.payloads,
                auth="Basic synthetic-test"),"updated")
            timer.write_text("synthetic owner staged timer")
            with self.assertRaisesRegex(
                    ValueError,"r4_schedule_units_must_be_recovered_first"):
                updater.rollback_completed_r4(auth="Basic synthetic-test")
            self.assertEqual(updater.registry()["release"],NEW)


if __name__=="__main__":
    unittest.main()
