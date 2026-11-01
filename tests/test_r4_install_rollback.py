"""Real updater.rollback() path after a synthetic R4 additive migration.

Only temporary files/SQLite in this test. Exercises exact code archive and
registry rollback plus a migrated journal, while preserving newer database
content. Never restores stale DB backup over a counted publish attempt.
"""
from __future__ import annotations

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
import bob_r4_schema as schema


def sha(blob):return hashlib.sha256(blob).hexdigest()


class R4CodeOnlyRollbackTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="r4-code-rollback-")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.bin=self.root/"bin"
        self.state=self.root/"state"
        self.bin.mkdir(mode=0o700)
        self.state.mkdir(mode=0o700)
        self.db_file=self.root/"activity-queue.sqlite3"
        with sqlite3.connect(self.db_file) as db:
            db.executescript("""
                CREATE TABLE publish_jobs(
                    run_id TEXT PRIMARY KEY,post_id TEXT,
                    attempted_at TEXT,comment_id TEXT);
                INSERT INTO publish_jobs VALUES(
                    '20261101T151033Z',
                    'bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a',
                    '2026-11-01T19:46:08+00:00',
                    '8c37f88f-e678-4007-ba56-586b76ef4cfd');
            """)
            self.assertEqual(schema.rehearsal(db),"ready")
        self.db_file.chmod(0o600)
        self.old={"bobctl":b"old exact bobctl source",
                  "bob_r4_schema.py":None}
        self.new={"bobctl":b"new exact bobctl source",
                  "bob_r4_schema.py":b"new R4 additive source"}
        self.tx=self.state/"tx-v0.8.0-autonomy1"
        self.tx.mkdir(mode=0o700)
        old_files={"bobctl":sha(self.old["bobctl"])}
        old_state={"format":updater.FORMAT,
                   "release":"v0.8.0-r3canary1","files":old_files}
        files={
            "bobctl":sha(self.new["bobctl"]),
            "bob_r4_schema.py":sha(self.new["bob_r4_schema.py"])}
        self.after={"format":updater.FORMAT,
                    "release":"v0.8.0-autonomy1","files":files}
        for name,data in self.new.items():
            (self.bin/name).write_bytes(data)
            (self.bin/name).chmod(0o700)
        def saved(path,data):
            path.write_bytes(data)
            path.chmod(0o600)
        saved(self.tx/"original.json",
              json.dumps({k:(sha(v) if v is not None else "absent")
                          for k,v in self.old.items()}).encode())
        saved(self.tx/"candidate.json",
              json.dumps({k:sha(v) for k,v in self.new.items()}).encode())
        saved(self.tx/"registry-before.json",
              json.dumps(old_state).encode())
        saved(self.tx/"old-bobctl",self.old["bobctl"])
        self.registry=self.state/"installed.json"
        saved(self.registry,json.dumps(self.after).encode())
        self.journal_file=self.state/"transaction.json"
        self.journal={"format":updater.FORMAT,
                      "release":"v0.8.0-autonomy1",
                      "phase":"migrated","restart_manager":True}

    def snapshot(self):
        with sqlite3.connect(self.db_file) as db:
            return (db.execute("SELECT * FROM publish_jobs").fetchall(),
                    schema.inspect(db))

    def test_updater_migrated_phase_code_only_rollback_preserves_db_and_receipt(self):
        before=self.snapshot()
        with patch.object(updater,"BIN",self.bin), \
             patch.object(updater,"STATE_DIR",self.state), \
             patch.object(updater,"REGISTRY",self.registry), \
             patch.object(updater,"JOURNAL",self.journal_file), \
             patch.object(updater,"restart_manager") as restarted, \
             patch.object(updater,"wait_for_health",return_value=True):
            outcome=updater.rollback(self.journal,auth="synthetic-none")
            self.assertEqual(outcome,"baseline_restored")
            self.assertEqual(updater.read_journal()["phase"],"rolled_back")
            restarted.assert_called_once()
        self.assertEqual((self.bin/"bobctl").read_bytes(),
                         self.old["bobctl"])
        self.assertFalse((self.bin/"bob_r4_schema.py").exists())
        self.assertEqual(json.loads(self.registry.read_text())["release"],
                         "v0.8.0-r3canary1")
        self.assertEqual(self.snapshot(),before)

    def test_code_rollback_rejects_drift_without_touching_sqlite(self):
        before=self.snapshot()
        (self.bin/"bobctl").write_bytes(b"untracked tampering")
        with patch.object(updater,"BIN",self.bin), \
             patch.object(updater,"STATE_DIR",self.state), \
             patch.object(updater,"REGISTRY",self.registry), \
             patch.object(updater,"JOURNAL",self.journal_file):
            with self.assertRaisesRegex(ValueError,
                                        "installed target changed outside transaction"):
                updater.rollback(self.journal,auth="none")
        self.assertEqual(self.snapshot(),before)


if __name__=="__main__":
    unittest.main()
