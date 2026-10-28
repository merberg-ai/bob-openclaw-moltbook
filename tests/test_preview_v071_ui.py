"""Read-only browser preview tests; no live service, API, or real database."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_v071_manager_candidate as builder
import preview_v071_ui as preview


class ReadonlyBrowserPreviewTests(unittest.TestCase):
    def test_fixture_is_private_deterministic_and_entirely_synthetic(self):
        with tempfile.TemporaryDirectory(prefix=preview.PREFIX) as temp:
            root = Path(temp)
            manifest = preview.prepare(root)
            self.assertEqual(manifest["preview_only"], "true")
            self.assertEqual(stat.S_IMODE((root / "PREVIEW-MARKER.json").stat().st_mode), 0o600)
            self.assertEqual((root / "bin/bob-activity-manager").read_bytes(), builder.build()[0])
            data = json.loads((root / "home/.config/moltbook/scout-result-" +
                               preview.FAKE_STAMP + ".json").read_text())
            self.assertEqual(data["chosen_post_id"], preview.FAKE_ID)
            self.assertEqual(data["chosen_author"], "Demo Agent")
            self.assertTrue(data["draft_comment"].startswith("A synthetic"))
            self.assertFalse((root / "home/.config/bob-system/lan-auth.json").exists())

    def test_actual_preview_http_get_and_post_guards(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/preview_v071_ui.py"), "--self-test"],
            cwd=ROOT, timeout=18, capture_output=True, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr[-1800:])
        self.assertIn("READ-ONLY UI BROWSER PREVIEW: PASS", result.stdout)
        self.assertIn("POST disabled: YES", result.stdout)
        self.assertIn("Private preview state removed.", result.stdout)

    def test_refuse_existing_stage_files(self):
        with tempfile.TemporaryDirectory(prefix=preview.PREFIX) as temp:
            root = Path(temp)
            (root / "unexpected").write_text("remain")
            with self.assertRaisesRegex(ValueError, "new private"):
                preview.prepare(root)
            self.assertEqual((root / "unexpected").read_text(), "remain")

    def test_marker_tampering_and_symlink_refused(self):
        with tempfile.TemporaryDirectory(prefix=preview.PREFIX) as temp:
            root = Path(temp)
            preview.prepare(root)
            marker = root / "PREVIEW-MARKER.json"
            marker.write_text(json.dumps({
                "type": preview.MARKER["type"],
                "production_allowed": True,
            }))
            with self.assertRaisesRegex(ValueError, "marker"):
                preview.assert_private(root)
            marker.unlink()
            marker.symlink_to(root / "bin/navigation_shell.py")
            with self.assertRaises(ValueError):
                preview.assert_private(root)

    def test_no_publish_or_service_control_in_preview_source(self):
        source = (ROOT / "scripts/preview_v071_ui.py").read_text()
        self.assertNotIn("systemctl", source)
        self.assertNotIn("systemd-run", source)
        self.assertNotIn("requests.post(", source)
        self.assertIn('self._send(405, "Read-only preview', source)
        self.assertIn('"127.0.0.1", 0', source)
        self.assertIn('BOB_MANAGER_BIND": "127.0.0.1"', source)

    def test_refuse_direct_child_call_without_marker(self):
        with tempfile.TemporaryDirectory(prefix=preview.PREFIX) as temp:
            with patch.dict(os.environ, {"BOB_V071_PREVIEW_CHILD": ""}):
                with patch.object(sys, "argv", [
                    "preview_v071_ui.py", "--_private-child", temp,
                ]):
                    self.assertEqual(preview.main(), 1)


if __name__ == "__main__":
    unittest.main()
