"""Offline tests for an inert Bob staging graph. Never run systemctl or live workers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stage_service_graph as stage
import stage_mock_actor as mock


class StageGraphTests(unittest.TestCase):
    def sandbox(self):
        return tempfile.TemporaryDirectory(prefix=stage.PREFIX)

    def test_ten_unique_units_no_production_unit_names(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            meta = stage.create(root)
            self.assertEqual(meta["service_count"], 6)
            self.assertEqual(meta["timer_count"], 4)
            self.assertFalse(meta["system_legacy_scout_included"])
            units = {p.name: p.read_text() for p in (root / "units").iterdir()}
            self.assertEqual(len(units), 10)
            self.assertEqual(set(units), set(meta["units_sha256"]))
            self.assertTrue(all(n.startswith(stage.PREFIX) for n in units))
            self.assertTrue(all("NEVER INSTALL OR ENABLE" in s for s in units.values()))
            self.assertTrue(all("bob-moltbook-scout.service" not in s for s in units.values()))
            stage.verify(root)

    def test_service_types_and_timers_from_sanitized_metadata(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            stage.create(root)
            for role in stage.RUNNING:
                s = (root / "units" / f"{stage.PREFIX}{role}.service").read_text()
                self.assertIn("Type=simple", s)
                self.assertIn("--serve", s)
            for role in stage.ONE_SHOT:
                s = (root / "units" / f"{stage.PREFIX}{role}.service").read_text()
                self.assertIn("Type=oneshot", s)
                self.assertIn("--once", s)
            for role, schedule in stage.TIMERS.items():
                s = (root / "units" / f"{stage.PREFIX}{role}.timer").read_text()
                self.assertIn("Unit=" + stage.PREFIX + role + ".service", s)
                for line in schedule:
                    self.assertIn(line, s)
            scout = (root / "units" / f"{stage.PREFIX}scout.service").read_text()
            self.assertIn("After=" + stage.PREFIX + "gateway.service", scout)
            self.assertNotIn("openclaw-gateway.service", scout)

    def test_full_isolated_fixture_rollback_preserves_synthetic_writes(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            stage.create(root)
            result = stage.rehearsal(root)
            self.assertEqual(result["mock_runs"], 14)
            self.assertTrue(result["health_failure_rollback"])
            self.assertTrue(result["post_swap_writes_preserved"])
            self.assertFalse(result["live_install_modified"])
            self.assertEqual(os.readlink(root / "current"), "releases/baseline")
            with sqlite3.connect(root / "private/synthetic.sqlite3") as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM simulated_events").fetchone()[0], 14)

    def test_corrupted_unit_or_extra_unit_rejected(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            stage.create(root)
            candidate = root / "units" / (stage.PREFIX + "publisher.timer")
            candidate.write_text(candidate.read_text() + "\nEnvironment=PRIVATE\n")
            with self.assertRaisesRegex(ValueError, "content drift"):
                stage.verify(root)
            candidate.write_text(stage.write_timer("publisher"))
            (root / "units/real-moltbook-worker.service").write_text("INERT?")
            with self.assertRaisesRegex(ValueError, "membership"):
                stage.verify(root)

    def test_mock_actor_rejects_modified_marker(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            stage.create(root)
            self.assertEqual(mock.run_once(root, "scout"), "baseline")
            (root / "STAGING-MARKER.json").write_text(json.dumps({
                "purpose": mock.MARKER, "production_allowed": True}))
            with self.assertRaisesRegex(ValueError, "marker"):
                mock.run_once(root, "scout")

    def test_mock_actor_rejects_untrusted_pointer(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            stage.create(root)
            (root / "current").unlink()
            (root / "current").symlink_to("/home/openclaw/.local/bin")
            with self.assertRaisesRegex(ValueError, "release pointer"):
                mock.validate(root)

    def test_root_and_existing_files_cannot_be_used_as_stage(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            (root / "existing.txt").write_text("must not delete")
            with self.assertRaisesRegex(ValueError, "nonempty"):
                stage.create(root)
            self.assertEqual((root / "existing.txt").read_text(), "must not delete")
            with self.assertRaises(ValueError):
                stage.create(Path.home())

    def test_bad_fixture_and_symlink_refused(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            fixture = root / "wrong.py"
            fixture.write_text("import requests\n")
            with self.assertRaisesRegex(ValueError, "Unexpected mock actor"):
                stage.create(root, source=fixture)
            fixture.unlink()
            fixture.symlink_to(stage.MOCK_SOURCE)
            with self.assertRaisesRegex(ValueError, "Unsafe mock actor"):
                stage.create(root, source=fixture)

    def test_script_does_not_import_live_modules_or_network(self):
        actor_text = stage.MOCK_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("import socket", actor_text)
        self.assertNotIn("import requests", actor_text)
        self.assertNotIn("urllib.request", actor_text)
        self.assertNotIn("subprocess", actor_text)
        self.assertNotIn("moltbook_api", actor_text)
        self.assertNotIn("bob_publish_common", actor_text)

    def test_permissions_private(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            stage.create(root)
            self.assertEqual(stat.S_IMODE((root / "private/synthetic.sqlite3").stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((root / "STAGING-MARKER.json").stat().st_mode), 0o600)
            self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600
                                for p in (root / "units").iterdir()))

    def test_mock_roles_restricted(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            stage.create(root)
            with self.assertRaisesRegex(ValueError, "Unknown mock role"):
                mock.run_once(root, "live-publisher")
            with self.assertRaisesRegex(ValueError, "Unrecognized mock role"):
                stage.run_fixture(root, "live-publisher")

    def test_mock_role_events_have_no_external_identifiers(self):
        with self.sandbox() as tmp:
            root = Path(tmp)
            stage.create(root)
            stage.rehearsal(root)
            with sqlite3.connect(root / "private/synthetic.sqlite3") as db:
                cols = [row[1] for row in db.execute("PRAGMA table_info(simulated_events)")]
                self.assertEqual(cols, ["id","role","release_tag"])
                roles = [r[0] for r in db.execute("SELECT DISTINCT role FROM simulated_events")]
                self.assertEqual(set(roles), mock.ROLES)


if __name__ == "__main__":
    unittest.main()
