"""R4 format1 signed source offer and isolated code-only updater acceptance.

No production host, OpenClaw, service, credentials, database or Moltbook
API is available. Everything is synthetic under a temporary directory.
"""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import report_r4_format_candidate as audit

NEW="v0.8.0-r4format1"
OLD="v0.8.0-r4propose1"


def signed_old_host():
    return {
        "release":OLD,
        "signed_installed_source":True,
        "legacy_and_r3_registry":True,
        "authenticated_https":True,
        "new_r4_routes":True,
        "versioned_additive_schema":True,
        "publisher_inactive_at_check":True,
        "new_r4_actions_attempted":0,
    }


class Format1SourceTests(unittest.TestCase):
    def test_prior_format1_offer_is_historical_not_repromoted(self):
        archived=json.loads((ROOT/
            "releases/candidates/r4-format1-json-reliability.json").read_text())
        self.assertEqual(archived["release"],NEW)
        self.assertEqual(archived["from"],OLD)
        self.assertEqual({x["name"]:x["source"] for x in archived["files"]},
                         audit.ALLOWED)
        live=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(live["release"],"v0.8.0-r4schedule2")
                schedule1=json.loads((ROOT/
            "releases/candidates/r4-schedule1-offfirst.json").read_text())
        self.assertEqual(schedule1["from"],archived["release"])
        self.assertEqual(live["from"],schedule1["release"])
        self.assertEqual(updater.manager_transport(NEW),"https")
        with self.assertRaisesRegex(ValueError,"r4_format_exact_offer_unverified"):
            audit.inspect()

    def test_old_host_preflight_gates_require_complete_signed_prior_release(self):
        for key,value in (
            ("release","v0.8.0-autonomy1"),
            ("signed_installed_source",False),
            ("legacy_and_r3_registry",False),
            ("authenticated_https",False),
            ("new_r4_routes",False),
            ("versioned_additive_schema",False),
            ("publisher_inactive_at_check",False),
            ("new_r4_actions_attempted",1),
        ):
            with self.subTest(key=key), \
                patch("report_r4_installed.inspect",
                      return_value={**signed_old_host(),key:value}), \
                patch.object(updater,"r4_publisher_inactive",return_value=True):
                self.assertFalse(updater.preflight_r4_format_patch())
        with patch("report_r4_installed.inspect",
                   return_value=signed_old_host()), \
             patch.object(updater,"r4_publisher_inactive",return_value=True):
            self.assertTrue(updater.preflight_r4_format_patch())
        with patch("report_r4_installed.inspect",
                   return_value=signed_old_host()), \
             patch.object(updater,"r4_publisher_inactive",return_value=False):
            self.assertFalse(updater.preflight_r4_format_patch())

    def test_no_model_or_network_in_source_audit(self):
        source=(ROOT/"scripts/report_r4_format_candidate.py").read_text()
        for banned in (
            "subprocess.run(", "requests.post(", "systemctl restart",
            "sqlite3.connect(", "set_pause(", "set_mode(", "api_key(",
            "openclaw_decide(", "updater.update(",
        ):
            self.assertNotIn(banned,source)
        self.assertEqual(audit.main(["--install"]),2)
        self.assertEqual(audit.main(["--check"]),1)


class Format1TransactionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r4-format1-isolated-")
        self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)
        self.bin=self.home/".local/bin"
        self.state=self.home/".local/state/bob-updater"
        self.db=self.home/".config/moltbook/activity-queue.sqlite3"
        self.backups=self.home/".local/state/bob-baseline/backups"
        for directory in (self.bin,self.state,self.db.parent):
            directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        with sqlite3.connect(self.db) as db:
            db.execute("CREATE TABLE proof (token TEXT)")
            db.execute("INSERT INTO proof VALUES ('old durable record')")
        self.db.chmod(0o600)
        self.offer=json.loads((ROOT/"releases/candidates/r4-format1-json-reliability.json").read_text())
        self.assertEqual(self.offer["release"],NEW)
        self.payloads={
            item["name"]:updater.release_bytes(ROOT,item)
            for item in self.offer["files"]
        }
        self.old_bytes={}
        for name in self.payloads:
            payload=("#!/usr/bin/env python3\n# synthetic signed old "+name+"\n").encode()
            self.old_bytes[name]=payload
            dest=self.bin/name
            dest.write_bytes(payload)
            dest.chmod(0o600)
        self.installed={"format":updater.FORMAT,"release":OLD,
                        "files":{name:hashlib.sha256(value).hexdigest()
                                 for name,value in self.old_bytes.items()}}
        (self.state/"installed.json").write_text(json.dumps(self.installed))
        (self.state/"installed.json").chmod(0o600)
        (self.state/"transaction.json").write_text(json.dumps(
            {"format":updater.FORMAT,"release":OLD,
             "phase":"complete","restart_manager":True}))
        (self.state/"transaction.json").chmod(0o600)

    def isolated_host(self,stack):
        for attribute,target in (
            ("BIN",self.bin),("STATE_DIR",self.state),
            ("LOCK",self.state/"lock"),
            ("REGISTRY",self.state/"installed.json"),
            ("JOURNAL",self.state/"transaction.json"),
            ("DB",self.db),("BACKUP_DIR",self.backups),
        ):
            stack.enter_context(patch.object(updater,attribute,target))
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

    def test_real_signed_bytes_install_and_code_only_reversal(self):
        with ExitStack() as stack:
            restart,backup=self.isolated_host(stack)
            self.assertEqual(updater.update(
                ROOT,self.installed,self.offer,self.payloads,
                auth="Basic synthetic-private"),"updated")
            installed=updater.registry()
            self.assertEqual(installed["release"],NEW)
            self.assertTrue(updater.live_ok(installed))
            self.assertEqual(updater.read_journal()["phase"],"complete")
            self.assertEqual(restart.call_count,1)
            backup.assert_called_once()
            for name,payload in self.payloads.items():
                self.assertEqual((self.bin/name).read_bytes(),payload)
            with sqlite3.connect(self.db) as db:
                self.assertEqual(
                    db.execute("SELECT token FROM proof").fetchone(),
                    ("old durable record",))
            # No schema mutation; verified private rollback restores ONLY
            # original registered code after the owner's separate choice.
            self.assertEqual(updater.rollback_completed_r4(
                auth="Basic synthetic-private"),"baseline_restored")
            self.assertEqual(updater.registry()["release"],OLD)
            self.assertEqual(updater.read_journal()["phase"],"rolled_back")
            self.assertEqual(restart.call_count,2)
            for name,payload in self.old_bytes.items():
                self.assertEqual((self.bin/name).read_bytes(),payload)
            with sqlite3.connect(self.db) as db:
                self.assertEqual(
                    db.execute("SELECT token FROM proof").fetchone(),
                    ("old durable record",))

    def test_candidate_fails_https_postflight_and_restores_previous_code(self):
        with ExitStack() as stack:
            restart,_=self.isolated_host(stack)
            health=stack.enter_context(patch.object(
                updater,"wait_for_health",
                side_effect=lambda auth,release=None: release==OLD))
            self.assertEqual(updater.update(
                ROOT,self.installed,self.offer,self.payloads,
                auth="Basic synthetic-private"),"rolled_back")
            self.assertEqual(updater.registry()["release"],OLD)
            self.assertEqual(updater.read_journal()["phase"],"rolled_back")
            self.assertEqual(restart.call_count,2)
            for name,payload in self.old_bytes.items():
                self.assertEqual((self.bin/name).read_bytes(),payload)


if __name__=="__main__":
    unittest.main()
