"""Synthetic offline source-candidate tests: no installed Bob files touched."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_source_candidate as candidate
import stage_live_sources as stage


class CandidateTests(unittest.TestCase):
    @staticmethod
    def lines_with_positions(positions, minimum=454):
        lines = ["# test source\n"] * minimum
        lines[0] = "#!/usr/bin/env python3\n"
        for n, text in positions.items():
            lines[n - 1] = text + "\n"
        return "".join(lines)

    def fixture(self, root: Path):
        home = root / "home"
        names = (
            "bin/bob-activity-manager",
            "bin/bob-lan-config",
            "bin/bob-moltbook-publisher",
            "bin/bob-moltbook-scout",
            "bin/bob-original-worker",
            "bin/bobctl",
            "lib/bob/bob_moltbook_api.py",
            "lib/bob/bob_originals.py",
            "lib/bob/bob_publish_common.py",
        )
        records = []
        lan = self.lines_with_positions({
            39: "print('Password:',json.loads(creds.read_text())['password'])",
            44: "print('LAN password:',json.loads(creds.read_text())['password'])",
        }, minimum=50)
        for name in names:
            path = home / ".local" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            source = (
                lan if name == "bin/bob-lan-config"
                else self.lines_with_positions({
                    453: "print('Password: do not disclose in support tickets')"
                }) if name == "bin/bobctl"
                else "#!/usr/bin/env python3\nprint('hi')\n"
            )
            path.write_text(source, encoding="utf-8")
            records.append({
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            })
        report = root / "inventory.json"
        report.write_text(json.dumps({"report_version": 1, "code_files": records}))
        original = stage.stage_sources(report, home, root / "private")
        return Path(original["path"]), hashlib.sha256(lan.encode()).hexdigest()

    def test_candidate_has_only_code_and_masks_known_password_statements(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot, test_lan_hash = self.fixture(root)
            old_hash = candidate.EXPECTED_LAN_PASSWORD_SHA256
            candidate.EXPECTED_LAN_PASSWORD_SHA256 = test_lan_hash
            try:
                destination = root / "candidate.zip"
                report = candidate.build_candidate(snapshot, destination)
            finally:
                candidate.EXPECTED_LAN_PASSWORD_SHA256 = old_hash
            self.assertEqual(report["source_count"], 9)
            with zipfile.ZipFile(destination) as zf:
                self.assertEqual(len(zf.namelist()), 10)
                lan = zf.read("bin/bob-lan-config").decode()
                self.assertEqual(lan.count("print('LAN password: [masked]')"), 2)
                self.assertNotIn("creds.read_text()", lan)
                bobctl = zf.read("bin/bobctl").decode()
                self.assertIn("do not disclose", bobctl)
                metadata = json.loads(zf.read("REVIEW-MANIFEST.json"))
                self.assertEqual(metadata["changed_lines"], [39, 44])
                self.assertEqual(len(metadata["sources"]), 9)
                self.assertFalse(any(name.endswith(".sqlite3") for name in zf.namelist()))

    def test_hash_drift_refused_before_zip_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot, _ = self.fixture(root)
            path = root / "out.zip"
            with self.assertRaisesRegex(ValueError, "LAN helper differs"):
                candidate.build_candidate(snapshot, path)
            self.assertFalse(path.exists())

    def test_mask_rejects_unexpected_password_print_lines(self):
        content = self.lines_with_positions({
            39: "print('Password:',creds['password'])",
            43: "print('Password:',creds['password'])",
        }, minimum=50)
        with self.assertRaisesRegex(ValueError, "Expected password print"):
            candidate.mask_lan_password_stdout(content)

    def test_mask_does_not_modify_arbitrary_password_assignments(self):
        content = self.lines_with_positions({
            39: "print('Password:',creds['password'])",
            44: "print('Password:',creds['password'])",
            45: "password = read_password()",
        }, minimum=50)
        result, lines = candidate.mask_lan_password_stdout(content)
        self.assertEqual(lines, [39, 44])
        self.assertIn("password = read_password()", result)
        self.assertEqual(result.count("[masked]"), 2)


if __name__ == "__main__":
    unittest.main()
