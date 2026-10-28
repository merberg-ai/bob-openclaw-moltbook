"""Synthetic, offline tests for redacted source-snapshot audit."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_staged_sources as audit
import stage_live_sources as stage


class RedactedAuditTests(unittest.TestCase):
    def make_archive(self, root: Path, content: str) -> Path:
        home = root / "home"
        scripts = home / ".local/bin"
        scripts.mkdir(parents=True)
        source = scripts / "bobctl"
        source.write_text(content, encoding="utf-8")
        inventory = root / "inventory.json"
        inventory.write_text(json.dumps({
            "report_version": 1,
            "created_utc": "2026-10-28T12:11:58Z",
            "code_files": [{
                "path": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "size_bytes": source.stat().st_size,
            }]
        }), encoding="utf-8")
        return Path(stage.stage_sources(inventory, home, root / "private")["path"])

    def test_reports_exact_locations_without_values(self):
        with tempfile.TemporaryDirectory() as temp:
            secret_literal = "FAKE_ONLY_NOT_A_REAL_CREDENTIAL_123456789"
            token = "ghp_" + "Z" * 27
            archive = self.make_archive(
                Path(temp),
                'print("synthetic")\ntoken = "' + secret_literal +
                '"\nprint("' + token + '")\n'
            )
            result = audit.audit_archive(archive)
            self.assertEqual(result["flag_count"], 2)
            self.assertEqual(result["files_checked"], 1)
            self.assertEqual(
                [(f["file"], f["line"]) for f in result["findings"]],
                [("bin/bobctl", 2), ("bin/bobctl", 3)]
            )
            serialized = json.dumps(result)
            self.assertNotIn(secret_literal, serialized)
            self.assertNotIn(token, serialized)

    def test_clean_source_returns_no_findings(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp), "print('hello world')\n")
            result = audit.audit_archive(archive)
            self.assertEqual(result["flag_count"], 0)

    def test_corrupt_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "bad.tar.gz"
            bad.write_bytes(b"not an archive")
            with self.assertRaises(Exception):
                audit.audit_archive(bad)


if __name__ == "__main__":
    unittest.main()
