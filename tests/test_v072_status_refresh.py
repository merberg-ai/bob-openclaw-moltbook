"""Focused acceptance for status UI refresh without service/DB mutations."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src/lib/bob"))
sys.path.insert(0, str(ROOT / "webui"))
import build_v072_live_candidate as live
import bob_status_view as view
import bob_live_status as status

class StatusRefreshTests(unittest.TestCase):
    def test_candidate_compiles_and_preserves_navigation(self):
        manager, nav = live.build()
        compile(manager, "bob-activity-manager", "exec")
        self.assertIn(b'elif self.path == "/assets/bob-status.js":', manager)
        self.assertIn(b'script-src \'self\'; connect-src \'self\'', manager)
        self.assertIn(b'if self.path == "/system/status"', manager)
        self.assertNotIn(b'meta http-equiv="refresh"', manager)
        self.assertIn(b'("/settings", "Settings", "Settings")', nav)

    def test_safe_html_and_external_script(self):
        html = view.page({
            "services": [{"name": "<script>alert(1)</script>", "state": "running"}],
            "queue": {"available": True, "jobs": [
                {"kind": "<img src=x>", "state": "queued", "created": "2026-10-28T18:00:00Z"}]}
        })
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('<img src=x>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('src="/assets/bob-status.js"', html)
        self.assertNotIn('http-equiv="refresh"', html)

    def test_js_updates_safe_text_and_auth_api(self):
        js = view.javascript()
        self.assertIn("textContent", js)
        self.assertIn("credentials: 'same-origin'", js)
        self.assertIn("cache: 'no-store'", js)
        self.assertNotIn("innerHTML", js)
        self.assertNotIn("POST", js)

    def test_idle_publisher_is_not_a_failure(self):
        with patch.object(status.subprocess, "run") as runner:
            runner.return_value.returncode = 3
            runner.return_value.stdout = "inactive\n"
            self.assertEqual(status.unit_state("bob-moltbook-publisher.service"), "idle")
            self.assertEqual(status.unit_state("bob-moltbook-publisher.timer"), "inactive")

if __name__ == "__main__":
    unittest.main()
