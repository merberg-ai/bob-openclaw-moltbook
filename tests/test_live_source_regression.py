"""Offline synthetic tests for the reviewed Bob source after import.

Never run the real workers or contact external services. This suite is skipped
until src/ exists on the source-import development branch.
"""
from contextlib import contextmanager
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "src/bin"
LIB = ROOT / "src/lib/bob"
SCRIPTS = (
    "bob-activity-manager", "bob-lan-config", "bob-moltbook-publisher",
    "bob-moltbook-scout", "bob-original-worker", "bobctl",
)
MODULES = ("bob_moltbook_api.py", "bob_originals.py", "bob_publish_common.py")


def load_module(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@contextmanager
def temp_database_modules():
    with tempfile.TemporaryDirectory() as home:
        with patch.dict(os.environ, {"HOME": home, "BOB_MANAGER_BIND": "127.0.0.1"}):
            with patch.object(sys, "path", [str(LIB)] + sys.path):
                for module in ("bob_publish_common", "bob_originals"):
                    sys.modules.pop(module, None)
                import bob_publish_common as common
                import bob_originals as originals
                try:
                    yield common, originals
                finally:
                    for module in ("bob_publish_common", "bob_originals"):
                        sys.modules.pop(module, None)


@unittest.skipUnless((BIN / "bobctl").is_file(), "Reviewed source not imported yet")
class ImportedSourceRegressionTests(unittest.TestCase):
    def test_exact_nine_python_sources_compile(self):
        for path in ([BIN / name for name in SCRIPTS]
                     + [LIB / name for name in MODULES]):
            with self.subTest(file=path.name):
                compile(path.read_bytes(), str(path), "exec")

    def test_password_not_printed_during_normal_status(self):
        with tempfile.TemporaryDirectory() as home:
            folder = Path(home) / ".config/bob-system"
            folder.mkdir(parents=True)
            secret = "TEST-ONLY-PASSWORD-THIS-IS-NOT-REAL-12345678"
            (folder / "lan-auth.json").write_text(json.dumps({
                "username": "bob", "password": secret,
            }))
            result = subprocess.run([sys.executable, str(BIN / "bob-lan-config"), "--show"],
                                    env={**os.environ, "HOME": home},
                                    capture_output=True, text=True, timeout=6)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(secret, result.stdout + result.stderr)
            self.assertIn("[masked]", result.stdout)

    def test_first_time_lan_enable_does_not_echo_generated_password(self):
        with tempfile.TemporaryDirectory() as home:
            fake = Path(home) / "test-bin"
            fake.mkdir()
            tool = fake / "systemctl"
            tool.write_text("#!/bin/sh\nexit 0\n")
            tool.chmod(0o755)
            env = {**os.environ, "HOME": home,
                   "PATH": str(fake) + os.pathsep + os.environ.get("PATH", "")}
            result = subprocess.run(
                [sys.executable, str(BIN / "bob-lan-config"),
                 "--enable", "--host", "192.168.60.25"],
                env=env, capture_output=True, text=True, timeout=6)
            self.assertEqual(result.returncode, 0, result.stderr)
            creds = json.loads(
                (Path(home) / ".config/bob-system/lan-auth.json").read_text())
            self.assertNotIn(creds["password"], result.stdout + result.stderr)
            self.assertIn("[masked]", result.stdout)

    def test_snapshot_hashes_and_manual_queue_duplicate_prevention(self):
        with temp_database_modules() as (common, originals):
            rid = "20261028T120000Z"
            pid = "12345678-1234-1234-1234-123456789abc"
            draft = "Synthetic example response that asks a question?"
            common.DATA.mkdir(parents=True, exist_ok=True)
            filename = "scout-feed-" + rid + ".json"
            feed = json.dumps({"posts": [{"id": pid}]}).encode()
            (common.DATA / filename).write_bytes(feed)
            feed_hash = hashlib.sha256(feed).hexdigest()
            approval = hashlib.sha256((pid + "\n" + draft + "\n" + feed_hash).encode()).hexdigest()
            record = {"schema": 2, "run_id": rid, "chosen_post_id": pid,
                      "draft_comment": draft, "snapshot_file": filename,
                      "snapshot_sha256": feed_hash,
                      "draft_sha256": hashlib.sha256(draft.encode()).hexdigest(),
                      "approval_sha256": approval, "status": "pending"}
            (common.DATA / ("scout-result-" + rid + ".json")).write_text(json.dumps(record))
            self.assertTrue(common.valid_record(record))
            self.assertFalse(common.valid_record({**record, "draft_comment": "tampered"}))
            with common.connect() as db:
                with self.assertRaises(ValueError):
                    common.queue_manual(db, rid)
                db.execute("INSERT INTO decisions VALUES(?,?,?,?)",
                           (rid, approval, "approved", common.now()))
                common.queue_manual(db, rid)
                with self.assertRaises(ValueError):
                    common.queue_manual(db, rid)
                self.assertEqual(db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0], 1)

    def test_original_post_approval_requires_digest(self):
        with temp_database_modules() as (common, originals):
            with common.connect() as db:
                originals.initialize(db)
                request = originals.request_draft(db, "thought")
                db.execute("UPDATE original_requests SET state='running' WHERE id=?", (request,))
                post = originals.add_draft(
                    db, request, "Synthetic title", "Example paragraph. " * 10, "general")
                digest = db.execute(
                    "SELECT digest FROM original_posts WHERE id=?", (post,)).fetchone()[0]
                with self.assertRaises(ValueError):
                    originals.transition(db, post, "approve", "wrong-digest")
                originals.transition(db, post, "approve", digest)
                with self.assertRaises(ValueError):
                    originals.transition(db, post, "approve", digest)


if __name__ == "__main__":
    unittest.main()
