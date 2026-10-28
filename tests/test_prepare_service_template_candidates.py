"""Offline tests for safe systemd candidate extraction; no systemctl or live units."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_service_template_candidates as review


SECRET = "DO-NOT-LEAK-FAKE-SECRET-123456789"
PRIVATE_PATH = "/home/synthetic/private/credentials"


class UnitCandidateTests(unittest.TestCase):
    def make_record(self, root: Path, scope: str, unit: str, body: str,
                    *, dropin: str | None = None) -> dict:
        if dropin:
            dest = root / (unit + ".d") / dropin
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            dest = root / unit
        dest.write_text(body, encoding="utf-8")
        return {"scope": scope, "unit": unit,
                "kind": "dropin" if dropin else "unit",
                "filename": dropin or unit,
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}

    def test_allowlisted_shapes_never_include_secret_or_private_path(self):
        body = (
            "[Unit]\n"
            "Description=Fake password " + SECRET + "\n"
            "After=network-online.target openclaw-gateway.service\n"
            "Wants=openclaw-gateway.service\n"
            "[Service]\n"
            "Type=oneshot\n"
            "ExecStart=/usr/bin/python3 " + PRIVATE_PATH + " --token " + SECRET + "\n"
            "Environment=BOB_TOKEN=" + SECRET + "\n"
            "EnvironmentFile=" + PRIVATE_PATH + "\n"
            "WorkingDirectory=" + PRIVATE_PATH + "\n"
            "NoNewPrivileges=yes\n"
            "Restart=no\n"
            "UnknownPrivateConfig=" + SECRET + "\n"
            "ExecStartPost=/bin/echo safe \\\n" + SECRET + "\n"
        )
        shape = review.sanitized_shape(body.encode())
        template = review.make_template("bob-moltbook-scout.service", "user", "unit", shape)
        serialized = json.dumps(shape) + template
        self.assertNotIn(SECRET, serialized)
        self.assertNotIn(PRIVATE_PATH, serialized)
        self.assertIn("After=network-online.target openclaw-gateway.service", template)
        self.assertIn("ExecStart=@REVIEW_REQUIRED_NOT_DEPLOYABLE@", template)
        self.assertIn("NoNewPrivileges=yes", template)
        self.assertNotIn("UnknownPrivateConfig", serialized)

    def test_full_private_zip_includes_only_review_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            usr, sysroot = root / "user", root / "system"
            usr.mkdir()
            sysroot.mkdir()
            units = [
                self.make_record(usr, "user", "bob-moltbook-scout.service",
                                 "[Service]\nType=oneshot\nExecStart=/usr/bin/python " +
                                 PRIVATE_PATH + " --token " + SECRET + "\n"),
                self.make_record(usr, "user", "bob-moltbook-scout.timer",
                                 "[Unit]\nAfter=network-online.target\n"
                                 "[Timer]\nOnCalendar=*:0/15\nPersistent=true\n"
                                 "[Install]\nWantedBy=timers.target\n"),
                self.make_record(sysroot, "system", "bob-moltbook-scout.timer",
                                 "[Timer]\nOnBootSec=3min\n"
                                 "ExecStart=/bin/echo " + SECRET + "\n"),
                self.make_record(usr, "user", "bob-activity-manager.service",
                                 "[Service]\nEnvironment=SECRET=" + SECRET + "\n",
                                 dropin="override.conf"),
            ]
            report = {"unit_files": units}
            manifest, templates = review.prepare(
                report, {"user": [usr], "system": [sysroot]}
            )
            self.assertEqual(manifest["source_count"], 4)
            self.assertFalse(manifest["deployable"])
            self.assertEqual(len(templates), 4)
            destination = root / "private-output"
            archive = review.private_output(destination, manifest, templates)
            self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)
            with zipfile.ZipFile(archive) as z:
                names = z.namelist()
                self.assertEqual(len(names), 5)
                all_content = "\n".join(z.read(n).decode() for n in names)
                self.assertNotIn(SECRET, all_content)
                self.assertNotIn(PRIVATE_PATH, all_content)
                self.assertIn("OnCalendar=*:0/15", all_content)
                self.assertIn("NOT DEPLOYABLE", all_content)
                self.assertIn("Env", all_content)

    def test_changed_source_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.mkdir(exist_ok=True)
            record = self.make_record(root, "user", "bob-moltbook-scout.service",
                                      "[Service]\nType=oneshot\n")
            roots = {"user": [root], "system": []}
            (root / record["unit"]).write_text("[Service]\nType=simple\n")
            with self.assertRaisesRegex(ValueError, "changed"):
                review.prepare({"unit_files": [record]}, roots)
            (root / record["unit"]).unlink()
            (root / record["unit"]).symlink_to(root / "not-there")
            with self.assertRaisesRegex(ValueError, "Symlink"):
                review.prepare({"unit_files": [record]}, roots)

    def test_unapproved_units_or_parent_path_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.mkdir(exist_ok=True)
            record = self.make_record(root, "user", "bob-moltbook-scout.service",
                                      "[Service]\nType=oneshot\n")
            invalid = {**record, "unit": "bob-PRIVATE-PASSWORD.service"}
            with self.assertRaisesRegex(ValueError, "Unexpected unit name"):
                review.prepare({"unit_files": [invalid]},
                               {"user": [root], "system": []})
            invalid = {**record, "kind": "dropin", "filename": "../steal.conf"}
            with self.assertRaisesRegex(ValueError, "drop-in filename"):
                review.prepare({"unit_files": [invalid]},
                               {"user": [root], "system": []})

    def test_refuse_insecure_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "published"
            root.mkdir()
            root.chmod(0o755)
            with self.assertRaises(PermissionError):
                review.private_output(root, {"test": True}, {"a.txt": "safe"})

    def test_reject_untrusted_timer_text_even_if_setting_is_known(self):
        shape = review.sanitized_shape((
            "[Timer]\nOnCalendar=*-*-* 05:00:00\n"
            "OnCalendar=*/home/private 01:00\n"
            "OnCalendar=*:0/15\nOnUnitActiveSec=15min\n"
            "OnCalendar=SECRETACCESSCODE123\n"
            "OnUnitInactiveSec=bad;touch /tmp/secret\n"
        ).encode())
        vals = shape["safe"]["Timer"]
        self.assertIn("*-*-* 05:00:00", vals["OnCalendar"])
        self.assertIn("*:0/15", vals["OnCalendar"])
        self.assertNotIn("*/home/private 01:00", vals["OnCalendar"])
        self.assertEqual(vals["OnUnitActiveSec"], ["15min"])
        self.assertEqual(shape["withheld_known_keys"]["OnCalendar"], 2)
        self.assertEqual(shape["withheld_known_keys"]["OnUnitInactiveSec"], 1)


if __name__ == "__main__":
    unittest.main()
