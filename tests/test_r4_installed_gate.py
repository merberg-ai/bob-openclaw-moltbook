"""R4 exact installed release attestation: synthetic private directory only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_installed_gate as gate


class R4AttestationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="r4-signed-gate-")
        self.addCleanup(t.cleanup)
        self.home=Path(t.name)
        state=self.home/".local/state/bob-updater"
        state.mkdir(parents=True)
        state.chmod(0o700)
        (self.home/".local/bin").mkdir(parents=True)
        self.registry=self.home/".local/state/bob-updater/installed.json"
        hashes={}
        for name in gate.REQUIRED:
            p=self.home/".local/bin"/name
            p.write_bytes(("fixed-source-"+name).encode())
            p.chmod(0o755)
            hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
        self.data={"format":"bob-updater-v1","release":gate.RELEASE,
                   "files":hashes}
        self.write_registry()

    def write_registry(self):
        self.registry.write_text(json.dumps(self.data))
        self.registry.chmod(0o600)

    def test_exact_synthetic_installed_registry_checks_all_files(self):
        self.assertTrue(gate.verify(home=self.home))
        self.assertGreater(len(gate.REQUIRED),10)

    def test_release_mismatch_or_missing_required_source_fails(self):
        self.data["release"]="v0.8.0-r3canary1"
        self.write_registry()
        self.assertFalse(gate.verify(home=self.home))
        self.data["release"]=gate.RELEASE
        self.data["files"].pop("bob-moltbook-publisher")
        self.write_registry()
        self.assertFalse(gate.verify(home=self.home))

    def test_code_tamper_or_bad_permissions_fails(self):
        p=self.home/".local/bin/bob_r4_remote_gate.py"
        p.write_text("changed untracked source")
        self.assertFalse(gate.verify(home=self.home))
        p.write_text("fixed-source-bob_r4_remote_gate.py")
        p.chmod(0o666)
        self.assertFalse(gate.verify(home=self.home))

    def test_journal_active_or_unprivate_registry_refused(self):
        journal=self.home/".local/state/bob-updater/transaction.json"
        journal.write_text("{}")
        self.assertFalse(gate.verify(home=self.home))
        journal.unlink()
        self.registry.chmod(0o644)
        self.assertFalse(gate.verify(home=self.home))

    def test_symlink_target_cannot_impersonate_installed_file(self):
        target=self.home/".local/bin/bob_r4_outbox.py"
        original=self.home/".local/bin/outbox-copy"
        original.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(original)
        self.assertFalse(gate.verify(home=self.home))


if __name__=="__main__":
    unittest.main()
