"""R4 private scheduling appears only as authenticated read-only status.

No real web server, credentials, SQLite, systemd or model call.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_web as web


class R4ScheduleWebTests(unittest.TestCase):
    def test_status_is_read_only_and_requires_explicit_terminal_install(self):
        html=web._schedule_status({"r4_schedule":{
            "phase":"staged","timer_enabled":False,
            "blockers":[]}})
        self.assertIn("R4 private proposal schedule",html)
        self.assertIn("STAGED",html)
        self.assertIn("OFF / not verified",html)
        self.assertIn("separately owner-confirmed terminal",html)
        self.assertNotIn('<form action="/r4/schedule',html)
        self.assertNotIn("Enable schedule</button>",html)

    def test_enabled_is_only_shown_for_verified_boolean(self):
        fake=web._schedule_status({"r4_schedule":{
            "phase":"enabled","timer_enabled":"true",
            "blockers":["schedule_status_unavailable"]}})
        self.assertIn("OFF / not verified",fake)
        verified=web._schedule_status({"r4_schedule":{
            "phase":"enabled","timer_enabled":True,
            "blockers":[]}})
        self.assertIn("Timer: <strong>ON</strong>",verified)

    def test_untrusted_status_fields_are_escaped_and_bounded(self):
        hostile=web._schedule_status({"r4_schedule":{
            "phase":"<script>untrusted</script>",
            "timer_enabled":False,
            "blockers":["<script>not safe</script>"]*60}})
        self.assertNotIn("<script>",hostile)
        self.assertIn("&lt;script&gt;",hostile)
        self.assertIn("UNVERIFIED",hostile)
        self.assertEqual(hostile.count("&lt;script&gt;not safe"),8)

    def test_no_r4_post_route_is_schedule_enable(self):
        self.assertNotIn("/r4/schedule/enable",web.PAGES)
        self.assertIsNone(web.ACTION_URL.fullmatch("/r4/schedule/enable"))
        self.assertIsNone(web.REVIEW_URL.fullmatch("/r4/schedule/enable"))
        self.assertIsNone(web.OUTBOX_URL.fullmatch("/r4/schedule/enable"))
        self.assertIsNone(web.SUGGEST_URL.fullmatch("/r4/schedule/enable"))


if __name__=="__main__":
    unittest.main()
