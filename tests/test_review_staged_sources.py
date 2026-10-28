"""Synthetic offline tests for the source review, without live services or secrets."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stage_live_sources as stage
import review_staged_sources as review


class SourceReviewTests(unittest.TestCase):
    def make_archive(self, temp: str, files: dict[str, str]) -> Path:
        home = Path(temp) / "home"
        manifest_files = []
        for relative, content in files.items():
            path = home / ".local" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            manifest_files.append({
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            })
        inventory = Path(temp) / "inventory.json"
        inventory.write_text(json.dumps({
            "report_version": 1,
            "code_files": manifest_files,
        }))
        return Path(stage.stage_sources(
            inventory, home, Path(temp) / "private-staging"
        )["path"])

    def test_runtime_password_reads_are_stdout_findings_not_hardcoded_literals(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = (
                "#!/usr/bin/env python3\n"
                "import json\n"
                "from pathlib import Path\n"
                "creds = Path('config.json')\n"
                "print('Password:',json.loads(creds.read_text())['password'])\n"
                "print('LAN password:',json.loads(creds.read_text())['password'])\n"
            )
            archive = self.make_archive(tmp, {"bin/bob-lan-config": source})
            report = review.review_snapshot(archive)
            self.assertEqual(report["language_counts"], {"python": 1})
            self.assertEqual(report["prior_heuristic_flags"], 2)
            self.assertEqual([f["line"] for f in report["findings"]], [5, 6])
            self.assertEqual(set(f["category"] for f in report["findings"]), {
                "possible credential-related stdout",
            })
            self.assertNotIn("config.json", json.dumps(report))

    def test_detects_literal_code_risks_and_unresolved_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = (
                "#!/usr/bin/env python3\n"
                "import os\n"
                "import requests\n"
                "import bob_moltbook_api\n"
                "API_TOKEN = 'not-a-real-secret-but-long'\n"
                "address = '192.168.1.24'\n"
                "base = '/home/example/private'\n"
                "exec('pass')\n"
            )
            archive = self.make_archive(tmp, {
                "bin/bobctl": code,
                "lib/bob/bob_moltbook_api.py": "from pathlib import Path\n",
            })
            report = review.review_snapshot(archive)
            self.assertEqual(report["possible_nonstdlib_imports"], ["requests"])
            self.assertEqual(set(f["category"] for f in report["findings"]), {
                "sensitive-named literal assignment",
                "non-loopback IP literal",
                "machine-specific absolute path",
                "dynamic Python execution",
            })
            for secret in ("not-a-real-secret-but-long", "192.168.1.24", "/home/example/private"):
                self.assertNotIn(secret, json.dumps(report))

    def test_unknown_and_shell_are_not_silently_certified(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self.make_archive(tmp, {
                "bin/bobctl": "#!/bin/bash\nsource ./private.sh\n",
                "bin/bob-helper": "this is not python\n",
            })
            result = review.review_snapshot(archive)
            self.assertEqual(result["language_counts"], {"shell": 1, "unknown": 1})
            self.assertEqual(len(result["findings"]), 2)

    def test_corrupt_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "invalid.tar.gz"
            bad.write_bytes(b"no")
            with self.assertRaises(Exception):
                review.review_snapshot(bad)


if __name__ == "__main__":
    unittest.main()
