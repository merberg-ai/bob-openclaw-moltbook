"""R2 opt-in Gateway experience injection: synthetic workspace files only.

No real OpenClaw workspace, live Gateway, credentials or Moltbook are touched.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from test_v08_shadow_core import prepare_sources, RUN, PID
from bob_v08 import gateway_bridge as bridge


class GatewayContextTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.workspace = root / "workspace"
        self.workspace.mkdir(mode=0o700)
        (self.workspace / "SOUL.md").write_text("Bob is curious and technical.\n")
        self.memory = self.workspace / "MEMORY.md"
        self.state = root / "state"
        self.source = root / "scout"
        self.source.mkdir(mode=0o700)
        prepare_sources(self.source)
        changes = {
            "WORKSPACE": self.workspace, "MEMORY": self.memory,
            "STATE": self.state, "CONFIG": self.state / "enabled.json",
            "LOCK": self.state / "lock", "BACKUP": self.state / "memory-before.bin",
            "SOURCE": self.source}
        for key, value in changes.items():
            p = patch.object(bridge, key, value)
            p.start()
            self.addCleanup(p.stop)

    def test_default_off_does_not_touch_workspace_on_import_or_status(self):
        self.assertEqual(bridge.status()["state"], "not_configured")
        self.assertFalse(self.memory.exists())
        self.assertFalse(self.state.exists())

    def test_enable_refresh_disable_preserve_owner_memory_and_soul(self):
        self.memory.write_text("Owner-approved prior memory.\n")
        soul = (self.workspace / "SOUL.md").read_bytes()
        self.assertEqual(bridge.enable(), "enabled")
        self.assertEqual(bridge.status()["state"], "enabled")
        data = self.memory.read_text()
        self.assertIn("Owner-approved prior memory.", data)
        self.assertEqual(data.count(bridge.BEGIN), 1)
        self.assertEqual(data.count(bridge.END), 1)
        self.assertIn(RUN, data)
        self.assertIn(PID, data)
        self.assertIn("topic_hints_not_verified", data)
        self.assertNotIn("An AI agent learns from experience", data)
        self.assertEqual(bridge.refresh(), "unchanged")
        self.assertEqual((self.workspace / "SOUL.md").read_bytes(), soul)
        self.assertEqual(self.memory.stat().st_mode & 0o077, 0)
        self.assertEqual(bridge.BACKUP.stat().st_mode & 0o077, 0)

        # Owner additions outside the managed block survive disable.
        self.memory.write_text(self.memory.read_text() + "\nNew owner note.\n")
        self.assertEqual(bridge.disable(), "disabled")
        after = self.memory.read_text()
        self.assertIn("Owner-approved prior memory.", after)
        self.assertIn("New owner note.", after)
        self.assertNotIn(bridge.BEGIN, after)
        self.assertEqual(bridge.enable(), "enabled")  # opt-in can be repeated

    def test_no_memory_file_restored_to_absence_on_disable(self):
        self.assertFalse(self.memory.exists())
        self.assertEqual(bridge.enable(), "enabled")
        self.assertTrue(self.memory.is_file())
        self.assertEqual(bridge.disable(), "disabled")
        self.assertFalse(self.memory.exists())

    def test_managed_block_change_refuses_destructive_disable(self):
        self.assertEqual(bridge.enable(), "enabled")
        contents = self.memory.read_text()
        self.memory.write_text(contents.replace("LOW-TRUST EVIDENCE", "ALTERED BLOCK"))
        with self.assertRaisesRegex(ValueError, "managed_context_was_edited"):
            bridge.disable()
        self.assertIn("ALTERED BLOCK", self.memory.read_text())

    def test_untrusted_prompt_injection_from_public_title_never_injected(self):
        data = bridge._managed_block()
        self.assertIn("BEGIN_UNTRUSTED_BOB_EXPERIENCE_JSON", data)
        self.assertNotIn("An AI agent learns from experience", data)
        self.assertNotIn("IGNORE PREVIOUS", data)
        self.assertIn("topic_hints_not_verified", data)

    def test_symlink_and_unknown_workspace_refuse(self):
        (self.workspace / "SOUL.md").unlink()
        with self.assertRaisesRegex(ValueError, "expected_openclaw_workspace"):
            bridge.enable()
        (self.workspace / "SOUL.md").write_text("Safe identity\n")
        outside = self.workspace / "outside.txt"
        outside.write_text("owner material")
        self.memory.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "unsafe_context_symlink"):
            bridge.enable()
        self.assertEqual(outside.read_text(), "owner material")

    def test_refresh_can_change_only_managed_block(self):
        self.memory.write_text("Preserved other memory\n")
        self.assertEqual(bridge.enable(), "enabled")
        original = self.memory.read_text()
        changed = bridge._managed_block().replace(
            "Bob's RECORDED Moltbook experience", "Bob's VERIFIED Moltbook experience")
        with patch.object(bridge, "_managed_block", return_value=changed):
            self.assertEqual(bridge.refresh(), "refreshed")
        revised = self.memory.read_text()
        self.assertIn("Preserved other memory", revised)
        self.assertIn("Bob's VERIFIED Moltbook", revised)
        self.assertNotEqual(revised, original)
        self.assertEqual(bridge.disable(), "disabled")
        self.assertIn("Preserved other memory", self.memory.read_text())


if __name__ == "__main__":
    unittest.main()
