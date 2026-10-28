"""Value-free host audit and inert systemd parser negative tests."""
from pathlib import Path
import hashlib
import json
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_live_unit_directive_names as names
import verify_inert_stage_units as unit_verify
import stage_service_graph as stage


class DirectiveNameAuditTests(unittest.TestCase):
    def test_no_known_or_unknown_directive_values_leave_report(self):
        secret = "PRIVATE_TEST_SECRET_7654321"
        text = f"""[Unit]
Description=Gateway with {secret}
After=network-online.target
[Service]
Environment=PASSWORD={secret}
ExecStart=/home/{secret}/script --secret {secret}
StrangeSecretKey={secret}
UnknownKey=multi \\
continued {secret}
Restart=always
[NonstandardSection]
MoreSecretKey={secret}
"""
        result = names.describe(text.encode())
        serialized = json.dumps(result)
        self.assertNotIn(secret, serialized)
        self.assertNotIn("StrangeSecretKey", serialized)
        self.assertNotIn("MoreSecretKey", serialized)
        service = result["known_directive_names_by_section"]["Service"]
        self.assertIn("Environment", service)
        self.assertIn("ExecStart", service)
        self.assertIn("Restart", service)
        self.assertEqual(result["unrecognized_directive_counts_by_section"]["Service"], 2)
        self.assertEqual(result["unrecognized_section_count"], 1)

    def test_only_exact_sha_verified_source_used(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unit = "openclaw-gateway.service"
            content = b"[Service]\nType=simple\nEnvironment=TOKEN=never-echo\n"
            (root / unit).write_bytes(content)
            record = {"scope":"user","unit":unit,"kind":"unit",
                      "filename":unit,"sha256":hashlib.sha256(content).hexdigest()}
            topology = {"unit_files":[record]}
            result = names.inspect(topology, {"user":[root],"system":[]})
            self.assertNotIn("never-echo",json.dumps(result))
            self.assertEqual(result["files_checked"],1)
            (root / unit).write_text("[Service]\nType=oneshot\n")
            with self.assertRaisesRegex(ValueError,"changed"):
                names.inspect(topology, {"user":[root],"system":[]})

    def test_unrecognized_unit_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"Unexpected unit record"):
                names.inspect(
                    {"unit_files":[{"scope":"system","unit":"untrusted-custom.service",
                                    "kind":"unit"}]},
                    {"user":[],"system":[Path(tmp)]})

    def test_private_report_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)/"private"
            report = {"purpose":"test-only","unit_files":[]}
            target = names.save_private(report,directory)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode),0o700)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode),0o600)
            self.assertEqual(json.loads(target.read_text()),report)


class InertSystemdParseTests(unittest.TestCase):
    def test_uses_only_systemd_analyze_and_explicit_ten_staging_files(self):
        class Result:
            returncode=0
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as temp:
            root=Path(temp)
            stage.create(root)
            with patch.object(unit_verify.subprocess,"run",return_value=Result()) as run:
                unit_verify.verify_with_parser(root,executable="/usr/bin/systemd-analyze")
            argv=run.call_args.args[0]
            self.assertEqual(argv[:2],["/usr/bin/systemd-analyze","verify"])
            self.assertEqual(len(argv),12)
            self.assertTrue(all(str(root/"units") in f for f in argv[2:]))
            self.assertEqual(run.call_args.kwargs["cwd"],root/"units")
            self.assertNotIn("shell",run.call_args.kwargs)

    def test_parser_nonzero_is_rejected_not_reported_verbatim(self):
        class Result:
            returncode=1
            stderr="PRIVATE PASSWORD MUST NOT PRINT"
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as temp:
            root=Path(temp)
            stage.create(root)
            with patch.object(unit_verify.subprocess,"run",return_value=Result()):
                with self.assertRaisesRegex(RuntimeError,"rejected"):
                    unit_verify.verify_with_parser(root,executable="/usr/bin/systemd-analyze")

    def test_untrusted_executable_name_rejected(self):
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as temp:
            root=Path(temp)
            stage.create(root)
            with self.assertRaisesRegex(RuntimeError,"missing or not allowed"):
                unit_verify.verify_with_parser(root,executable="/bin/systemctl")

    def test_stage_unit_modification_is_blocked_before_parser_call(self):
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as temp:
            root=Path(temp)
            stage.create(root)
            unit=root/"units"/(stage.PREFIX+"scout.timer")
            unit.write_text(unit.read_text()+"\nExecStart=/bin/untrusted\n")
            with patch.object(unit_verify.subprocess,"run") as run:
                with self.assertRaisesRegex(ValueError,"content drift"):
                    unit_verify.verify_with_parser(root,executable="/usr/bin/systemd-analyze")
                run.assert_not_called()


if __name__=="__main__":
    unittest.main()
