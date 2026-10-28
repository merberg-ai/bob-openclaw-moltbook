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

    def test_realistic_python_cache_is_ignored_but_sources_remain_hash_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "bin").mkdir()
            lib = root / "lib/bob"
            lib.mkdir(parents=True)
            source = root / "bin/bobctl"
            source.write_bytes(self.synthetic_sources()["bin/bobctl"])
            cache = lib / "__pycache__"
            cache.mkdir()
            (cache / "bob_originals.cpython-311.pyc").write_bytes(b"bytecode")
            with patch.dict(r.SOURCES, self.synthetic_hashes(), clear=True):
                self.assertEqual(r.source_bytes(root), self.synthetic_sources())
                source.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    r.source_bytes(root)

    def test_cache_symlink_and_nonbytecode_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "bin").mkdir()
            lib = root / "lib/bob"
            lib.mkdir(parents=True)
            (root / "bin/bobctl").write_bytes(self.synthetic_sources()["bin/bobctl"])
            cache = lib / "__pycache__"
            cache.mkdir()
            with patch.dict(r.SOURCES, self.synthetic_hashes(), clear=True):
                (cache / "other.txt").write_text("not bytecode")
                with self.assertRaisesRegex(ValueError, "Unexpected Python cache entry"):
                    r.source_bytes(root)
                (cache / "other.txt").unlink()
                (cache / "valid.pyc").write_bytes(b"bytecode")
                (cache / "symlink.pyc").symlink_to(cache / "valid.pyc")
                with self.assertRaisesRegex(ValueError, "Unexpected Python cache entry"):
                    r.source_bytes(root)
                (cache / "symlink.pyc").unlink()
                (cache / "valid.pyc").unlink()
                cache.rmdir()
                cache.symlink_to(root / "bin", target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "Unexpected Python cache type"):
                    r.source_bytes(root)

    def test_unreviewed_file_remains_refused_even_when_cache_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "bin").mkdir()
            lib = root / "lib/bob"
            lib.mkdir(parents=True)
            (root / "bin/bobctl").write_bytes(self.synthetic_sources()["bin/bobctl"])
            cache = lib / "__pycache__"
            cache.mkdir()
            (cache / "valid.pyc").write_bytes(b"bytecode")
            (lib / "unexpected.py").write_text("not reviewed")
            with patch.dict(r.SOURCES, self.synthetic_hashes(), clear=True):
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
