"""Read-only production plan regression: no real service or file writes."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "v071_production_plan", ROOT / "scripts/plan_v071_production_deployment.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class ProductionPlanTests(unittest.TestCase):
    def test_plan_refuses_external_backup_without_query(self):
        with patch.object(mod, "query") as query:
            with self.assertRaises(ValueError):
                mod.plan(Path("/tmp/not-an-approved-backup.sqlite3"))
            query.assert_not_called()

    def test_plan_refuses_relative_backup(self):
        with patch.object(mod, "query") as query:
            with self.assertRaises(ValueError):
                mod.plan(Path("backup.sqlite3"))
            query.assert_not_called()

    def test_plan_refuses_invalid_file_extension(self):
        with patch.object(mod, "query") as query:
            with self.assertRaises(ValueError):
                mod.plan(mod.APPROVED_BACKUP_DIR / "bob-activity-test.txt")
            query.assert_not_called()

    def test_no_deploy_mode_available(self):
        self.assertFalse(hasattr(mod, "deploy"))
        self.assertEqual(mod.APPROVED_UNIT, "bob-activity-manager.service")

    def test_source_candidate_is_distinct(self):
        candidate, nav = mod.builder.build()
        self.assertNotEqual(mod.builder.sha256(candidate),
                            mod.builder.PINNED_BASELINE_SHA256)
        self.assertIn(b"integrate_existing_html", nav)

    def test_field_names_are_fixed(self):
        self.assertEqual(len(mod.FIELDS), 7)
        self.assertEqual(len(set(mod.FIELDS)), 7)


if __name__ == "__main__":
    unittest.main()
