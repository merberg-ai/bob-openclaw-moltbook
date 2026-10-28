"""Offline synthetic tests only, with no real host or external API calls."""

from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backup_live_sqlite as backup


class VerifiedBackupTests(unittest.TestCase):
    def make_db(self, directory):
        p = Path(directory) / "live" / "activity-queue.sqlite3"
        p.parent.mkdir(parents=True)
        with sqlite3.connect(p) as conn:
            conn.execute("CREATE TABLE publish_jobs (id INTEGER PRIMARY KEY, secret TEXT)")
            conn.execute("INSERT INTO publish_jobs(secret) VALUES ('synthetic-private-post')")
            conn.execute("PRAGMA user_version=0")
        return p

    def test_private_online_backup_and_restore_rehearsal(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_db(tmp)
            out = Path(tmp) / "private-backups"
            result = backup.create_verified_backup(source, out)
            self.assertEqual(result["tables"], 1)
            self.assertEqual(result["user_version"], 0)
            self.assertEqual(result["restore_rehearsal"], "passed")
            saved = Path(result["backup_path"])
            self.assertTrue(saved.is_file())
            self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
            with sqlite3.connect(saved) as conn:
                self.assertEqual(
                    conn.execute("SELECT secret FROM publish_jobs").fetchone()[0],
                    "synthetic-private-post",
                )
            with sqlite3.connect(source) as conn:
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM publish_jobs").fetchone()[0], 1
                )
            self.assertFalse(
                any(p.name.startswith(".restore-") for p in out.iterdir())
            )

    def test_rejects_unprotected_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_db(tmp)
            out = Path(tmp) / "public"
            out.mkdir(mode=0o755)
            out.chmod(0o755)
            with self.assertRaises(PermissionError):
                backup.create_verified_backup(source, out)

    def test_refuses_symlink_source_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_db(tmp)
            link = Path(tmp) / "linked.sqlite3"
            link.symlink_to(source)
            out = Path(tmp) / "private"
            with self.assertRaises(FileNotFoundError):
                backup.create_verified_backup(link, out)
            out.mkdir(mode=0o700)
            out_link = Path(tmp) / "out-link"
            out_link.symlink_to(out, target_is_directory=True)
            with self.assertRaises(PermissionError):
                backup.create_verified_backup(source, out_link)

    def test_corrupt_file_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "not-sqlite.sqlite3"
            source.write_text("definitely not sqlite")
            out = Path(tmp) / "private"
            with self.assertRaises(sqlite3.DatabaseError):
                backup.create_verified_backup(source, out)
            self.assertEqual(list(out.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
