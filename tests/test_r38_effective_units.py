"""R3.8 effective service/drop-in audit: sanitized, allowlisted, read-only."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import inspect
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from report_r38_effective_units import audit, report, SERVICE, TIMER, _cat

SERVICE_TEXT = """# /home/operator/.config/systemd/user/bob-moltbook-publisher.service
[Unit]
Description=Bob publisher test fixture
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/bob/src/bin/bob-moltbook-publisher
Restart=no
Environment=AUTH_TOKEN=DO_NOT_ECHO
[Install]
WantedBy=default.target
"""
TIMER_TEXT = """# /home/operator/.config/systemd/user/bob-moltbook-publisher.timer
[Unit]
Description=Bob publisher test fixture timer
[Timer]
Unit=bob-moltbook-publisher.service
OnBootSec=2min
OnUnitActiveSec=1min
[Install]
WantedBy=timers.target
"""


class EffectiveUnitTests(unittest.TestCase):
    def test_known_safe_shapes_and_zero_live_authority(self):
        result=audit(SERVICE_TEXT,TIMER_TEXT)
        self.assertTrue(result.service_valid)
        self.assertTrue(result.timer_valid)
        self.assertEqual(result.blockers,())
        self.assertEqual(result.environment_directives,1)
        self.assertEqual(result.service_dropins,0)
        self.assertFalse(result.cutover_authorized)
        self.assertFalse(result.modifies_host)

    def test_supported_systemd_execstart_reset_in_dropin(self):
        amended=SERVICE_TEXT+"""# /home/operator/.config/systemd/user/bob-moltbook-publisher.service.d/10-override.conf
[Service]
ExecStart=
ExecStart=/usr/bin/python3 /new/release/bob-moltbook-publisher
"""
        result=audit(amended,TIMER_TEXT)
        self.assertTrue(result.service_valid)
        self.assertEqual(result.service_dropins,1)

    def test_duplicate_effective_exec_and_unapproved_binary_block(self):
        duplicate=SERVICE_TEXT+"""# /etc/systemd/user/bob-moltbook-publisher.service.d/additional.conf
[Service]
ExecStart=/usr/bin/python3 /opt/bob/src/bin/bob-moltbook-publisher
"""
        self.assertIn("publisher_exec_not_verified",audit(
            duplicate,TIMER_TEXT).blockers)
        other=SERVICE_TEXT.replace(
            "/opt/bob/src/bin/bob-moltbook-publisher","/opt/bob/misc/unaudited-script")
        self.assertIn("publisher_exec_not_verified",audit(other,TIMER_TEXT).blockers)

    def test_shell_wrapper_and_extra_code_bypass_are_blocked(self):
        wrapped=SERVICE_TEXT.replace(
            "ExecStart=/usr/bin/python3 /opt/bob/src/bin/bob-moltbook-publisher",
            "ExecStart=/bin/bash -c /opt/bob/src/bin/bob-moltbook-publisher")
        self.assertIn("publisher_exec_not_verified",audit(
            wrapped,TIMER_TEXT).blockers)
        post=SERVICE_TEXT+"\n[Service]\nExecStartPost=/bin/curl https://example.invalid\n"
        self.assertIn("extra_publisher_process_command",audit(
            post,TIMER_TEXT).blockers)
        override=SERVICE_TEXT+"\n[Service]\nRestart=always\n"
        self.assertIn("publisher_restart_policy_needs_review",audit(
            override,TIMER_TEXT).blockers)

    def test_bad_timer_unit_and_empty_schedule_never_pass(self):
        wrong=TIMER_TEXT.replace(
            "Unit=bob-moltbook-publisher.service","Unit=bob-r3-candidate-publisher.service")
        self.assertIn("publisher_timer_wrong_target",audit(
            SERVICE_TEXT,wrong).blockers)
        missing=TIMER_TEXT.replace("OnBootSec=2min","").replace("OnUnitActiveSec=1min","")
        self.assertIn("publisher_timer_no_schedule",audit(
            SERVICE_TEXT,missing).blockers)
        service_ok=audit(SERVICE_TEXT,wrong)
        self.assertTrue(service_ok.service_valid)
        self.assertFalse(service_ok.timer_valid)

    def test_no_raw_secrets_or_paths_emitted(self):
        def fake_run(command, **options):
            self.assertEqual(command[0:3],["systemctl","--user","cat"])
            self.assertIn(command[3],(SERVICE,TIMER))
            self.assertTrue(options["capture_output"])
            self.assertEqual(options["timeout"],4)
            return SimpleNamespace(
                returncode=0,
                stdout=SERVICE_TEXT if command[3]==SERVICE else TIMER_TEXT)
        result=report(run=fake_run)
        self.assertEqual(result["effective_service"],"reviewed_shape")
        self.assertEqual(result["effective_timer"],"reviewed_shape")
        self.assertFalse(result["cutover_authorized"])
        self.assertNotIn("DO_NOT_ECHO",str(result))
        self.assertNotIn("/home/operator",str(result))
        self.assertNotIn("AUTH_TOKEN",str(result))
        self.assertEqual(result["service_changes"],0)

    def test_absent_unit_and_unrecognized_replacement_fail_closed(self):
        def missing(*_args,**_kwargs):
            return SimpleNamespace(returncode=1,stdout="",stderr="access denied")
        data=report(run=missing)
        self.assertEqual(data["effective_service"],"unverified")
        self.assertEqual(data["effective_timer"],"unverified")
        self.assertTrue(data["review_blockers"])
        self.assertFalse(data["cutover_authorized"])
        with self.assertRaisesRegex(ValueError,"unapproved_unit"):
            _cat("bob-arbitrary-timer.timer",run=missing)

    def test_root_scope_or_unit_status_does_not_issue_write_commands(self):
        import report_r38_effective_units as module
        script=inspect.getsource(module)
        for dangerous in ("systemctl enable", "systemctl start", "systemctl stop",
                          "systemctl daemon-reload", "systemctl restart",
                          "api_key(", "urllib.request", "requests."):
            self.assertNotIn(dangerous,script)
        self.assertEqual(module.SERVICE,"bob-moltbook-publisher.service")


if __name__=="__main__":
    unittest.main()
