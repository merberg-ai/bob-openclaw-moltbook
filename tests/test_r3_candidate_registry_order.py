"""Offline R3 package registry / updater transaction / rollback acceptance.

Runs REAL updater transaction against disposable filesystem and SQLite only.
All systemd, network and private backup interactions are mocked. Demonstrates
that versioned package hashes are recorded before a simulated manager restart,
that failed health restores code and registry, and that SQLite is NEVER rolled
back after a simulated new attempted publication event.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
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
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as upd
import backup_live_sqlite as backup


OLD_MANAGER=b"stable TLS-only synthetic manager"
NEW_MANAGER=b"new TLS-only synthetic candidate"
OLD_ARCHIVE=b"stable verified R3 package"
NEW_ARCHIVE=b"new signed synthetic R3 package"


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


class CandidateTransactionTests(unittest.TestCase):
    def setUp(self):
        work=tempfile.TemporaryDirectory(prefix="bob-r3-registry-test-")
        self.addCleanup(work.cleanup)
        root=Path(work.name)
        self.bin=root/"bin"
        self.bin.mkdir(mode=0o700)
        self.state=root/"state"
        self.state.mkdir(mode=0o700)
        self.registry=self.state/"installed.json"
        self.journal=self.state/"transaction.json"
        self.lock=self.state/"lock"
        self.db=root/"synthetic.sqlite3"
        self.backup_dir=root/"backups"
        with sqlite3.connect(self.db) as db:
            db.execute("CREATE TABLE attempts(event TEXT PRIMARY KEY)")
            db.execute("INSERT INTO attempts VALUES ('before')")
        self.current={
            "format":upd.FORMAT,"release":"v0.8.0-chhttps3",
            "files":{
                "bob-activity-manager":sha(OLD_MANAGER),
                "bob_r3_package.pyz":sha(OLD_ARCHIVE),
            },
        }
        for name,blob in (("bob-activity-manager",OLD_MANAGER),
                          ("bob_r3_package.pyz",OLD_ARCHIVE)):
            target=self.bin/name
            target.write_bytes(blob)
            target.chmod(0o700)
        self.registry.write_text(json.dumps(self.current),encoding="utf-8")
        self.registry.chmod(0o600)
        self.plan={"release":"v0.8.0-cutover1","restart_manager":True}
        self.contents={"bob-activity-manager":NEW_MANAGER,
                       "bob_r3_package.pyz":NEW_ARCHIVE}
        self.patches=[
            patch.object(upd,"BIN",self.bin),
            patch.object(upd,"STATE_DIR",self.state),
            patch.object(upd,"REGISTRY",self.registry),
            patch.object(upd,"JOURNAL",self.journal),
            patch.object(upd,"LOCK",self.lock),
            patch.object(upd,"DB",self.db),
            patch.object(upd,"BACKUP_DIR",self.backup_dir),
            patch.object(backup,"create_verified_backup",side_effect=self.backup),
            patch.object(upd,"healthy",side_effect=self.healthy),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.backups=[]
        self.restarts=[]
        self.health_checks=[]

    def backup(self, src, dest):
        self.assertEqual((src,dest),(self.db,self.backup_dir))
        self.backups.append("verified_private_backup_simulated")
        return None

    def healthy(self, auth, *, release=None):
        self.assertEqual(auth,"Basic synthetic")
        self.health_checks.append(release)
        return release=="v0.8.0-chhttps3"

    def record_after_update(self):
        with sqlite3.connect(self.db) as db:
            db.execute("INSERT OR IGNORE INTO attempts VALUES ('after')")

    def db_attempts(self):
        with sqlite3.connect(self.db) as db:
            return [r[0] for r in db.execute(
                "SELECT event FROM attempts ORDER BY event")]

    def restart(self):
        # This is the critical condition: the MANAGER loads the new ZIP and
        # compares its hash to the currently installed registry on startup.
        entry=upd.registry()
        self.assertTrue(upd.live_ok(entry))
        self.restarts.append(entry["release"])

    def run_update(self, *, restart=None, health=None):
        with patch.object(upd,"restart_manager",side_effect=restart or self.restart), \
             patch.object(upd,"wait_for_health",side_effect=health or (
                     lambda auth, *, release: True)), \
             redirect_stdout(StringIO()):
            return upd.update(ROOT,self.current,self.plan,self.contents,
                              auth="Basic synthetic")

    def test_staged_registry_hash_exists_before_manager_restarts(self):
        self.assertEqual(self.run_update(),"updated")
        self.assertEqual(self.restarts,["v0.8.0-cutover1"])
        self.assertEqual(self.backups,["verified_private_backup_simulated"])
        self.assertEqual(self.health_checks,["v0.8.0-chhttps3"])
        self.assertEqual(upd.registry()["release"],"v0.8.0-cutover1")
        self.assertEqual(upd.read_journal()["phase"],"complete")
        self.assertEqual((self.bin/"bob_r3_package.pyz").read_bytes(),NEW_ARCHIVE)
        self.assertEqual(self.db_attempts(),["before"])

    def test_failed_https_health_rolls_back_code_and_registry_not_database(self):
        def simulated_restart():
            self.restart()
            if len(self.restarts)==1:
                self.record_after_update()
        def health(auth, *, release):
            return release=="v0.8.0-chhttps3"
        self.assertEqual(
            self.run_update(restart=simulated_restart,health=health),
            "rolled_back")
        self.assertEqual(self.restarts,
                         ["v0.8.0-cutover1","v0.8.0-chhttps3"])
        self.assertEqual(upd.registry(),self.current)
        self.assertEqual((self.bin/"bob-activity-manager").read_bytes(),OLD_MANAGER)
        self.assertEqual((self.bin/"bob_r3_package.pyz").read_bytes(),OLD_ARCHIVE)
        self.assertEqual(self.db_attempts(),["after","before"])
        self.assertEqual(upd.read_journal()["phase"],"rolled_back")

    def test_interrupted_restart_can_be_recovered_without_rewinding_attempts(self):
        def crash():
            self.restart()
            self.record_after_update()
            raise KeyboardInterrupt("synthetic power loss after signed registry")
        with self.assertRaises(KeyboardInterrupt):
            self.run_update(restart=crash)
        journal=upd.read_journal()
        self.assertEqual(journal["phase"],"installed")
        self.assertEqual(upd.registry()["release"],"v0.8.0-cutover1")
        with patch.object(upd,"restart_manager",side_effect=self.restart), \
             patch.object(upd,"wait_for_health",return_value=True):
            self.assertEqual(upd.rollback(journal,auth="Basic synthetic"),
                             "baseline_restored")
        self.assertEqual(self.restarts,
                         ["v0.8.0-cutover1","v0.8.0-chhttps3"])
        self.assertEqual(upd.registry(),self.current)
        self.assertEqual(upd.read_journal()["phase"],"rolled_back")
        self.assertEqual(self.db_attempts(),["after","before"])

    def test_restart_exception_does_not_leave_new_signed_registry_active(self):
        def broken_restart():
            self.restart()
            if len(self.restarts)==1:
                self.record_after_update()
                raise RuntimeError("synthetic bad service startup")
        result=self.run_update(restart=broken_restart)
        self.assertEqual(result,"rolled_back")
        self.assertEqual(upd.registry(),self.current)
        self.assertEqual(upd.read_journal()["phase"],"rolled_back")
        self.assertEqual(self.db_attempts(),["after","before"])

if __name__=="__main__":
    unittest.main()
