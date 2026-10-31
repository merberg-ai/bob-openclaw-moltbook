"""CH-HTTPS0 read-only OMEN TLS readiness contract tests.

All systemd, socket, HTTP, filesystem and installed-updater reads mocked;
never contacts real network, accesses operator secrets, or changes services.
"""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import MagicMock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_ch_https0 as audit


def good_observation():
    return {
        "account":"expected_openclaw",
        "installed_release":"v0.8.0-r3stage1",
        "r3_schema":"ready",
        "migration_journal":"complete",
        "r3_dispatch_authorized":False,
        "manager_service":"active",
        "publisher_timer":"active",
        "scout_timer":"active",
        "current_manager_transport":"authenticated_http_r3",
        "listener":"lan_or_wildcard",
        "certificate_state":"not_prepared",
    }


class TLS0ReadOnlyTests(unittest.TestCase):
    def test_current_http_accepted_only_as_preparation_not_tls_activation(self):
        report=audit.evaluate(good_observation())
        self.assertEqual(report["source_preflight"],"pass")
        self.assertEqual(report["next_reviewed_phase"],
                         "tls_aware_updater_before_any_tls_cutover")
        self.assertFalse(report["tls_activated"])
        self.assertFalse(report["new_r3_send_rights"])
        self.assertEqual(report["live_service_changes"],0)
        self.assertEqual(report["live_database_changes"],0)
        self.assertEqual(report["windows_browser_ca_trust"],
                         "not_checked_on_host")

    def test_unknown_or_incomplete_host_state_cannot_activate(self):
        for key,value in (
                ("account","unverified"),
                ("installed_release","unverified"),
                ("r3_schema","eligible"),
                ("r3_schema","refused"),
                ("migration_journal","prepared"),
                ("r3_dispatch_authorized",True),
                ("manager_service","inactive"),
                ("publisher_timer","disabled"),
                ("scout_timer","inactive"),
                ("current_manager_transport","not_verified")):
            with self.subTest(key=key,value=value):
                data=good_observation()
                data[key]=value
                actual=audit.evaluate(data)
                self.assertEqual(actual["source_preflight"],"needs_review")
                self.assertFalse(actual["tls_activated"])

    def test_certificate_presence_never_implies_browser_trust(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(
                audit,"TLS_DIR",Path(tmp)/"tls"):
            self.assertEqual(audit._materials(),"not_prepared")
            root=audit.TLS_DIR
            root.mkdir(mode=0o700)
            self.assertEqual(audit._materials(),"incomplete")
            for name in audit.TLS_NAMES:
                target=root/name
                target.write_bytes(b"synthetic not a certificate")
                target.chmod(0o600)
            self.assertEqual(audit._materials(),
                             "present_needs_certificate_validation")
            (root/"server.key").chmod(0o644)
            self.assertEqual(audit._materials(),"untrusted")
            (root/"server.key").chmod(0o600)
            (root/"server.crt").unlink()
            (root/"server.crt").symlink_to(root/"ca.crt")
            self.assertEqual(audit._materials(),"incomplete")

    def test_authenticated_r3_probe_is_loopback_get_and_sanitized(self):
        good=MagicMock()
        good.status=200
        good.read.return_value=b"<title>Bob R3 Controls</title> R3 automatic publishing compiled locked"
        conn=MagicMock()
        conn.getresponse.return_value=good
        with patch.object(audit.updater,"authorization",
                          return_value="Basic private_secret_never_print"),\
             patch.object(audit,"HTTPConnection",return_value=conn):
            self.assertEqual(audit._loopback_http(),"authenticated_http_r3")
        args,kwargs=conn.request.call_args
        self.assertEqual(args[:2],("GET","/r3"))
        self.assertEqual(kwargs["headers"]["Host"],"127.0.0.1:18790")
        self.assertEqual(conn.read.call_count,0)
        good.read.return_value=b"Owner controls remain unavailable" + (
            b"Bob R3 Controls R3 automatic publishing compiled locked")
        with patch.object(audit.updater,"authorization",return_value="Basic secret"),\
             patch.object(audit,"HTTPConnection",return_value=conn):
            self.assertEqual(audit._loopback_http(),"not_verified")

    def test_listener_classifies_only_fixed_port(self):
        for output,expected in (
            ("LISTEN 0 4096 0.0.0.0:18790 0.0.0.0:*\n","lan_or_wildcard"),
            ("LISTEN 0 4096 127.0.0.1:18790 0.0.0.0:*\n","loopback_only"),
            ("","not_listening")):
            with patch.object(audit.subprocess,"run",
                 return_value=MagicMock(returncode=0,stdout=output)):
                self.assertEqual(audit._listener(),expected)
        with patch.object(audit.subprocess,"run") as run:
            run.side_effect=OSError("synthetic unavailable")
            self.assertEqual(audit._listener(),"unverified")

    def test_no_mutating_cli_flags(self):
        with patch.object(audit,"collect") as inspect:
            self.assertEqual(audit.main(["--enable"]),2)
            self.assertEqual(audit.main(["--install"]),2)
            inspect.assert_not_called()


if __name__=="__main__":
    unittest.main()
