"""Synthetic, offline tests for the read-only v0.7.1 host gate."""
import importlib.util
from pathlib import Path
import os
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/preflight_v071_live.py"
spec = importlib.util.spec_from_file_location("preflight_v071_live", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class PreflightTests(unittest.TestCase):
    def test_pinned_manager_and_drift_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = Path(tmp) / "manager"
            data = b"known test manager"
            manager.write_bytes(data)
            with patch.object(gate, "EXPECTED_MANAGER_SHA256", gate.hashlib.sha256(data).hexdigest()):
                self.assertTrue(gate.check_manager(manager))
                manager.write_bytes(data + b" changed")
                self.assertFalse(gate.check_manager(manager))
                manager.unlink()
                manager.symlink_to(Path(tmp) / "elsewhere")
                self.assertFalse(gate.check_manager(manager))

    def test_backup_private_integrity_and_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "private"
            folder.mkdir(mode=0o700)
            backup = folder / "test.sqlite3"
            with sqlite3.connect(backup) as db:
                db.execute("CREATE TABLE t (value TEXT)")
                db.execute("INSERT INTO t VALUES ('fictional')")
            backup.chmod(0o600)
            now = time.time()
            self.assertTrue(gate.check_backup(backup, now=now))
            self.assertFalse(gate.check_backup(backup, now=now + 90000))
            backup.chmod(0o644)
            self.assertFalse(gate.check_backup(backup, now=now))
            backup.chmod(0o600)
            folder.chmod(0o755)
            self.assertFalse(gate.check_backup(backup, now=now))
            folder.chmod(0o700)
            link = folder / "link.sqlite3"
            link.symlink_to(backup)
            self.assertFalse(gate.check_backup(link, now=now))
            backup.write_bytes(b"not sqlite")
            self.assertFalse(gate.check_backup(backup, now=now))

    def test_service_status_strict_matching(self):
        class Result:
            returncode = 0
            stdout = "LoadState=loaded\nActiveState=active\nSubState=running\n"
        with patch.object(gate.subprocess, "run", return_value=Result()):
            self.assertTrue(gate.check_service())
            Result.stdout = "LoadState=loaded\nActiveState=active\nSubState=exited\n"
            self.assertFalse(gate.check_service())
            Result.stdout = "LoadState=loaded\nActiveState=active\nSubState=running\nExecStart=secret"
            self.assertFalse(gate.check_service())

    def test_refused_gate_is_not_approved(self):
        with patch.object(gate, "check_manager", return_value=True), \
             patch.object(gate, "check_backup", return_value=False):
            result = gate.run(Path("/dummy/manager"), Path("/dummy/backup"),
                              service_check=lambda: True)
        self.assertFalse(all(result.values()))


if __name__ == "__main__":
    unittest.main()
