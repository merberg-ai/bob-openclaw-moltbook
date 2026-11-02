"""Offline coverage for v0.7.1 transaction safety. No live host access."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts/rehearse_v071_transaction_safety.py"
spec = importlib.util.spec_from_file_location("v071_tx_lab", path)
lab = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


class TransactionSafetyTests(unittest.TestCase):
    def test_healthy_candidate(self):
        result, restarts, checks = lab.simulate("healthy")
        self.assertEqual((result, restarts, checks), ("candidate_healthy", 1, 1))

    def test_failed_health_rolls_back_once(self):
        self.assertEqual(lab.simulate("failed-health"), ("rolled_back", 2, 2))

    def test_failed_recovery_is_incident(self):
        self.assertEqual(lab.simulate("failed-recovery"), ("recovery_failed", 2, 2))

    def test_unresolved_transaction_refuses_resume(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-journal-") as temp:
            root = Path(temp)
            lab.journal(root, "candidate_selected", "healthy")
            with self.assertRaises(ValueError):
                lab.run(root, "healthy", lab.FakeService((True,)))

    def test_existing_lock_refuses_second_writer(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-journal-") as temp:
            root = Path(temp)
            with lab.exclusive(root):
                with self.assertRaises(ValueError):
                    with lab.exclusive(root):
                        pass

    def test_symlink_journal_refused(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-journal-") as temp:
            root = Path(temp)
            (root / "transaction.json").symlink_to(root / "elsewhere")
            with self.assertRaises(ValueError):
                lab.read_journal(root)

    def test_stale_pending_file_refused(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-journal-") as temp:
            root = Path(temp)
            (root / ".journal-pending").write_text("stale")
            with self.assertRaises(ValueError):
                lab.journal(root, "prepared", "healthy")

    def test_retry_budget(self):
        fake = lab.FakeService((False, False, True))
        fake.restart()
        fake.restart()
        with self.assertRaises(AssertionError):
            fake.restart()
        fake.healthy()
        fake.healthy()
        with self.assertRaises(AssertionError):
            fake.healthy()

    def test_private_dir_required(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-journal-") as temp:
            root = Path(temp)
            root.chmod(0o755)
            with self.assertRaises(ValueError):
                lab.secure_root(root)

if __name__ == "__main__":
    unittest.main()
