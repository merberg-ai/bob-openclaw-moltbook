"""Offline tests of guarded Git branch reconciliation."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reconcile_dev_checkout as sync


class SyncGuardTests(unittest.TestCase):
    def test_clean_identical_trees_and_ref_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "bob-v070-inventory"
            root.mkdir()
            def g(*args):
                p = subprocess.run(["git", *args], cwd=root,
                                   capture_output=True, text=True, check=True)
                return p.stdout.strip()
            g("init", "-q")
            g("config", "user.name", "Synthetic")
            g("config", "user.email", "synthetic@example.invalid")
            (root / "source.txt").write_text("same content\n")
            g("add", "source.txt")
            g("commit", "-qm", "initial")
            g("switch", "-qc", sync.FEATURE)
            g("commit", "--allow-empty", "-qm", "synthetic local")
            local = g("rev-parse", "HEAD")
            g("commit", "--allow-empty", "-qm", "synthetic remote")
            remote = g("rev-parse", "HEAD")
            g("reset", "--hard", local)
            g("update-ref", f"refs/remotes/origin/{sync.FEATURE}", remote)
            with patch.object(sync, "LOCAL_REVIEWED", local[:7]), \
                 patch.object(sync, "REMOTE_REVIEWED", remote), \
                 patch.object(sync, "BACKUP", "backup/test-reviewed"), \
                 patch.object(sync.Path, "cwd", return_value=root):
                old_git = sync.git
                def repo_git(*args, check=True):
                    return subprocess.run(["git", *args], cwd=root, text=True,
                                          capture_output=True, timeout=15, check=check)
                with patch.object(sync, "git", side_effect=repo_git):
                    self.assertEqual(sync.main(), 0)
                    self.assertEqual(g("rev-parse", "HEAD"), remote)
                    self.assertEqual(g("rev-parse", "backup/test-reviewed"), local)
                    self.assertEqual(g("status", "--porcelain"), "")

    def test_refuses_dirty_worktree_before_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "bob-v070-inventory"
            root.mkdir()
            def g(*args):
                return subprocess.run(["git", *args], cwd=root,
                                      capture_output=True, text=True, check=True).stdout.strip()
            g("init", "-q")
            g("config", "user.name", "Synthetic")
            g("config", "user.email", "synthetic@example.invalid")
            (root / "file").write_text("content\n")
            g("add", "file")
            g("commit", "-qm", "initial")
            g("switch", "-qc", sync.FEATURE)
            local = g("rev-parse", "HEAD")
            (root / "untracked").write_text("do not touch")
            with patch.object(sync.Path, "cwd", return_value=root):
                def repo_git(*args, check=True):
                    return subprocess.run(["git", *args], cwd=root, text=True,
                                          capture_output=True, timeout=15, check=check)
                with patch.object(sync, "git", side_effect=repo_git):
                    with self.assertRaisesRegex(ValueError, "local changes"):
                        sync.validate()
            self.assertEqual(g("rev-parse", "HEAD"), local)
            self.assertTrue((root / "untracked").exists())


if __name__ == "__main__":
    unittest.main()
