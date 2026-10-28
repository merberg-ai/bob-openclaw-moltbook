"""Synthetic, offline tests for independent private ZIP audit."""
from pathlib import Path
import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_service_candidate_zip as audit
import prepare_service_template_candidates as extractor


class CandidateZipAuditTests(unittest.TestCase):
    def build(self, root: Path):
        unit = "bob-moltbook-scout.timer"
        body = "[Unit]\nAfter=network-online.target\n[Timer]\nOnCalendar=*:0/15\nPersistent=yes\n[Install]\nWantedBy=timers.target\n"
        source = root/"units"
        source.mkdir()
        source_file = source/unit
        source_file.write_text(body)
        record = {"scope":"user","kind":"unit","unit":unit,
                  "filename":unit,
                  "sha256":hashlib.sha256(body.encode()).hexdigest()}
        topology = {"report_version":1,
                    "purpose":"private read-only Bob service topology; not a deployable unit template",
                    "unit_files":[record]}
        report = root/"inventory-20261028.json"
        report.write_text(json.dumps(topology))
        report.chmod(0o600)
        manifest, candidates = extractor.prepare(
            topology, {"user":[source],"system":[]}
        )
        output = root/"private"
        archive = extractor.private_output(output, manifest, candidates)
        return archive,report

    def rewrite(self, path: Path, edit):
        with zipfile.ZipFile(path) as z:
            members = {name:z.read(name) for name in z.namelist()}
        edit(members)
        with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
            for name,data in members.items():
                z.writestr(name,data)
        path.chmod(0o600)

    def test_normal_zip_passes_with_original_topology_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            self.assertEqual(audit.audit(archive,report),1)

    def test_raw_exec_or_environment_value_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            def tamper(members):
                name = next(x for x in members if x.endswith(".template.txt"))
                members[name] += b"\n[Service]\nExecStart=/bin/sh -c unexpected\n"
            self.rewrite(archive,tamper)
            with self.assertRaisesRegex(ValueError,"Unapproved"):
                audit.audit(archive,report)

    def test_private_host_path_rejected_in_a_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            def tamper(members):
                name = next(x for x in members if x.endswith(".template.txt"))
                members[name] += b"\n[Unit]\nDescription=/home/synthetic/secret.txt\n"
            self.rewrite(archive,tamper)
            with self.assertRaisesRegex(ValueError,"Unapproved"):
                audit.audit(archive,report)

    def test_manifest_source_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            def tamper(members):
                m = json.loads(members[audit.MANIFEST])
                m["unit_templates"][0]["raw_unit_sha256"] = "0"*64
                members[audit.MANIFEST] = json.dumps(m).encode()
            self.rewrite(archive,tamper)
            with self.assertRaisesRegex(ValueError,"topology"):
                audit.audit(archive,report)

    def test_unexpected_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            def tamper(members):
                members["SECRET.txt"] = b"private"
            self.rewrite(archive,tamper)
            with self.assertRaisesRegex(ValueError,"membership"):
                audit.audit(archive,report)

    def test_deployable_true_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            def tamper(members):
                m = json.loads(members[audit.MANIFEST])
                m["deployable"] = True
                members[audit.MANIFEST] = json.dumps(m).encode()
            self.rewrite(archive,tamper)
            with self.assertRaisesRegex(ValueError,"review status"):
                audit.audit(archive,report)

    def test_world_readable_archive_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            archive.chmod(0o644)
            with self.assertRaisesRegex(ValueError,"private regular"):
                audit.audit(archive,report)

    def test_unapproved_comment_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            def tamper(members):
                name = next(x for x in members if x.endswith(".template.txt"))
                members[name] += b"# MY_PRIVATE_TOKEN=abcdef\n"
            self.rewrite(archive,tamper)
            with self.assertRaisesRegex(ValueError,"comment"):
                audit.audit(archive,report)

    def test_invalid_timer_schedule_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive,report = self.build(Path(tmp))
            def tamper(members):
                name = next(x for x in members if x.endswith(".template.txt"))
                members[name] = members[name].replace(b"OnCalendar=*:0/15",
                                                       b"OnCalendar=SECRETFILE")
            self.rewrite(archive,tamper)
            with self.assertRaisesRegex(ValueError,"Unapproved"):
                audit.audit(archive,report)


if __name__=="__main__":
    unittest.main()
