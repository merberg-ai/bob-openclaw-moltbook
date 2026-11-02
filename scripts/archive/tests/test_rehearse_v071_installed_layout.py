"""Synthetic transaction tests. Never touch host services."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "scripts"))
spec = importlib.util.spec_from_file_location(
    "rehearse_v071_installed_layout", root / "scripts/rehearse_v071_installed_layout.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class InstalledLayoutTests(unittest.TestCase):
    def test_failed_health_restores_original(self):
        outcome = mod.rehearse(fail_health=True)
        self.assertTrue(outcome["synthetic_health_failure_rollback"])
        self.assertTrue(outcome["original_manager_preserved"])

    def test_healthy_selection_stays_candidate(self):
        outcome = mod.rehearse(fail_health=False)
        self.assertFalse(outcome["synthetic_health_failure_rollback"])
        self.assertTrue(outcome["no_production_change"])

    def test_existing_file_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "file"
            file.write_text("unchanged")
            with self.assertRaises(ValueError):
                mod.put(file, b"replacement", 0o600)
            self.assertEqual(file.read_text(), "unchanged")

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-installed-") as temp:
            stage = Path(temp)
            (stage / "installed").mkdir(mode=0o700)
            (stage / "releases/v071").mkdir(mode=0o700, parents=True)
            (stage / "installed/bob-activity-manager").symlink_to(
                stage / "releases/v071/navigation_shell.py")
            with self.assertRaises(ValueError):
                mod.verify(stage, b"candidate", b"nav")


if __name__ == "__main__":
    unittest.main()
