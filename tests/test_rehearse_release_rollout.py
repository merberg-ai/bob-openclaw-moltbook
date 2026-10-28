"""Synthetic isolated update/rollback tests (no installed service interaction)."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rehearse_release_rollout as r
from import_verified_sources import SOURCES


class RehearsalTests(unittest.TestCase):
    def synthetic_sources(self):
        return {"bin/bobctl": b"#!/usr/bin/env python3\nprint('synthetic')\n"}

    def synthetic_hashes(self):
        return {name: hashlib.sha256(data).hexdigest()
                for name, data in self.synthetic_sources().items()}

    def test_update_failure_rolls_back_code_and_keeps_post_upgrade_db_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "rehearsal"
            with patch.dict(r.SOURCES, self.synthetic_hashes(), clear=True):
                result = r.run_rehearsal(root, self.synthetic_sources())
                self.assertEqual(r.active(root), "baseline")
                r.verify_release(root, "baseline")
            self.assertTrue(result["atomic_switch_verified"])
            self.assertTrue(result["failed_health_rollback_verified"])
            self.assertTrue(result["post_upgrade_writes_preserved"])

    def test_corrupted_candidate_refused_without_changing_active_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = self.synthetic_sources()
            with patch.dict(r.SOURCES, self.synthetic_hashes(), clear=True):
                r.stage_release(root, "baseline", files)
                r.stage_release(root, "candidate", files)
                r.swap(root, "baseline")
                (root / "releases/candidate/bin/bobctl").write_bytes(b"corrupted")
                with self.assertRaises(ValueError):
                    r.swap(root, "candidate")
                self.assertEqual(r.active(root), "baseline")

    def test_source_membership_and_hash_are_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, digest in SOURCES.items():
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("synthetic source\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                r.source_bytes(root)
            (root / "bin/unreviewed").write_text("unreviewed")
            with self.assertRaisesRegex(ValueError, "membership"):
                r.source_bytes(root)

    def test_refuses_stale_current_or_unexpected_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = self.synthetic_sources()
            with patch.dict(r.SOURCES, self.synthetic_hashes(), clear=True):
                r.stage_release(root, "baseline", files)
                (root / "current").write_text("not a symlink")
                with self.assertRaisesRegex(ValueError, "unexpected current"):
                    r.swap(root, "baseline")
                with self.assertRaisesRegex(ValueError, "must be empty"):
                    r.run_rehearsal(root, files)


if __name__ == "__main__":
    unittest.main()
