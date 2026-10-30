"""R2 session-scoped MD1: no global memory writes, no Moltbook publishing."""
from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from bob_v08 import experience
from test_v08_shadow_core import prepare_sources, RUN


class SessionExperienceTests(unittest.TestCase):
    def test_real_agent_adapter_receives_one_bounded_session_prompt(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            prepare_sources(path)
            model = Mock(return_value="I observed one saved Scout selection.")
            reply = experience.ask_once(source=path, model=model)
            self.assertIn("observed", reply)
            model.assert_called_once()
            prompt, session = model.call_args.args
            self.assertIn("OWNER-REQUESTED PRIVATE EXPERIENCE REVIEW", prompt)
            self.assertIn(RUN, prompt)
            self.assertIn("Do not use tools", prompt)
            self.assertIn("Never claim that a draft was published", prompt)
            self.assertTrue(session.startswith("moltbook-v08-experience-"))
            self.assertLess(len(prompt), 6500)
            self.assertFalse((path / "MEMORY.md").exists())
            self.assertFalse((path / "activity-queue.sqlite3").exists())

    def test_without_source_still_returns_honest_unknowns(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            calls = Mock(return_value="No verified observations.")
            experience.ask_once(source=path, model=calls)
            prompt = calls.call_args.args[0]
            self.assertIn("unknown", prompt.lower())
            self.assertIn("[]", prompt)
            self.assertFalse((path / "activity-queue.sqlite3").exists())

    def test_experience_and_shadow_code_cannot_edit_workspace_memory(self):
        for name in ("experience.py", "shadow.py", "digest.py"):
            raw = (ROOT / "src/bob_v08" / name).read_text()
            self.assertNotIn(' / "MEMORY.md"', raw)
            self.assertNotIn(' / "SOUL.md"', raw)
            self.assertNotIn("api_key(", raw)
            self.assertNotIn("moltbook.com", raw)
        self.assertFalse((ROOT / "src/bob_v08/gateway_bridge.py").exists())


if __name__ == "__main__":
    unittest.main()
