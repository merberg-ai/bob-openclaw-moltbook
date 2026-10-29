"""Synthetic, fully offline tests of reviewed-source ZIP import."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_verified_sources as importer


class VerifiedSourceImportTests(unittest.TestCase):
    def fixture(self):
        originals = {}
        for name in importer.SOURCES:
            if name == "bin/bob-lan-config":
                text = "#!/usr/bin/env python3\n" + "print('LAN password: [masked]')\n" * 2
            else:
                text = "#!/usr/bin/env python3\nprint('synthetic')\n"
            originals[name] = text.encode("utf-8")
        hashes = {name: hashlib.sha256(data).hexdigest()
                  for name, data in originals.items()}
        manifest = {
            "source_count": 9,
            "changed_file": "bin/bob-lan-config",
            "changed_lines": [39, 44],
            "sources": [{"path": n, "candidate_sha256": h}
                        for n, h in hashes.items()],
        }
        return originals, hashes, manifest

    @staticmethod
    def make_zip(files, manifest, extra=None, symlink=False):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as bundle:
            for name, data in files.items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = ((0o120777 if symlink and name == "bin/bobctl"
                                       else 0o100644) << 16)
                bundle.writestr(info, data)
            bundle.writestr(importer.MANIFEST, json.dumps(manifest))
            if extra:
                bundle.writestr(extra, "should never get extracted")
        return out.getvalue()

    def test_accepts_exact_reviewed_source_only(self):
        files, hashes, manifest = self.fixture()
        with patch.dict(importer.SOURCES, hashes, clear=True):
            verified = importer.preflight(self.make_zip(files, manifest))
        self.assertEqual(verified, files)

    def test_rejects_changed_code_and_unexpected_files(self):
        files, hashes, manifest = self.fixture()
        with patch.dict(importer.SOURCES, hashes, clear=True):
            changed = dict(files)
            changed["bin/bobctl"] = b"print('changed')"
            with self.assertRaises(ValueError):
                importer.preflight(self.make_zip(changed, manifest))
            with self.assertRaises(ValueError):
                importer.preflight(self.make_zip(files, manifest, extra="../private.json"))

    def test_rejects_symlink_archive_entries(self):
        files, hashes, manifest = self.fixture()
        with patch.dict(importer.SOURCES, hashes, clear=True):
            with self.assertRaises(ValueError):
                importer.preflight(self.make_zip(files, manifest, symlink=True))

    def test_import_only_writes_into_target_checkout_src(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            contents = {"bin/bobctl": b"print('synthetic')\n",
                        "lib/bob/bob_moltbook_api.py": b"pass\n"}
            importer.import_to_checkout(root, contents)
            self.assertEqual((root / "src/bin/bobctl").read_bytes(), contents["bin/bobctl"])
            self.assertEqual((root / "src/lib/bob/bob_moltbook_api.py").read_bytes(),
                             contents["lib/bob/bob_moltbook_api.py"])
            with self.assertRaises(FileExistsError):
                importer.import_to_checkout(root, contents)

    def test_rejects_wrong_branch_or_dirty_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def wrong_branch(_root, *args):
                return "main"
            with patch.object(importer, "git", side_effect=wrong_branch):
                with self.assertRaises(ValueError):
                    importer.require_clean_feature_branch(root)
            def dirty(_root, *args):
                if "branch" in args: return "feature/v0.7.0-host-inventory"
                if "rev-parse" in args: return str(root)
                return "?? private-file"
            with patch.object(importer, "git", side_effect=dirty):
                with self.assertRaises(ValueError):
                    importer.require_clean_feature_branch(root)


if __name__ == "__main__":
    unittest.main()
