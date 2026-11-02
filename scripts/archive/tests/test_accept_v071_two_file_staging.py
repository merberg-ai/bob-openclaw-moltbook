"""Offline regression tests for versioned two-file staging acceptance."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "accept_v071_two_file_staging",
    ROOT / "scripts/accept_v071_two_file_staging.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TwoFileAcceptanceTests(unittest.TestCase):
    def test_complete_staging_and_code_rollback(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            result = mod.acceptance(Path(tmp))
            self.assertTrue(all(result.values()))

    def test_missing_navigation_refused(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            root = Path(tmp)
            manager, nav = mod.builder.build()
            mod.make_stage(root, mod.builder.SOURCE.read_bytes(), manager, nav)
            mod.switch(root, "candidate")
            (root / "releases/candidate/bin/navigation_shell.py").unlink()
            with self.assertRaises(ValueError):
                mod.verify_import(root)

    def test_modified_navigation_refused(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            root = Path(tmp)
            manager, nav = mod.builder.build()
            mod.make_stage(root, mod.builder.SOURCE.read_bytes(), manager, nav)
            mod.switch(root, "candidate")
            (root / "releases/candidate/bin/navigation_shell.py").write_text(
                "def other(): pass"
            )
            with self.assertRaises(ValueError):
                mod.verify_import(root)

    def test_baseline_selection_is_not_candidate(self):
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            root = Path(tmp)
            manager, nav = mod.builder.build()
            mod.make_stage(root, mod.builder.SOURCE.read_bytes(), manager, nav)
            mod.switch(root, "baseline")
            with self.assertRaises(ValueError):
                mod.verify_import(root)


if __name__ == "__main__":
    unittest.main()
