"""R1 updater channel and manifest compatibility acceptance.

Local temporary Git origin only; no GitHub, Moltbook, Ollama, systemd, live DB,
credentials or installed Bob files are accessed.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bob_release_updater as updater


def git(*args, cwd=None):
    return subprocess.run(["git", *map(str, args)], cwd=cwd, text=True,
                          capture_output=True, timeout=15, check=True).stdout.strip()


class LocalGitFixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.repo = base / "checkout"
        self.remote = base / "upstream.git"
        self.config = base / "private-config.json"
        self.lock = base / "lock"
        git("init", "--bare", "--initial-branch=main", self.remote)
        git("init", "--initial-branch=main", self.repo)
        git("config", "user.name", "Synthetic Test", cwd=self.repo)
        git("config", "user.email", "fixture@example.invalid", cwd=self.repo)
        (self.repo / "state.txt").write_text("stable main\n")
        git("add", "state.txt", cwd=self.repo)
        git("commit", "-m", "stable", cwd=self.repo)
        git("remote", "add", "origin", self.remote, cwd=self.repo)
        git("push", "-u", "origin", "main", cwd=self.repo)
        self.conf = {"format": updater.FORMAT, "checkout": str(self.repo)}
        self.write_config()
        for name, value in (
            ("CONFIG", self.config),
            ("ORIGINS", frozenset({str(self.remote)})),
            ("registry", lambda: {"format": updater.FORMAT, "release": "v0.7.7",
                                  "files": {}}),
            ("live_ok", lambda state: True),
            ("read_journal", lambda: None),
            ("locked", lambda: os.open(self.lock, os.O_RDWR | os.O_CREAT, 0o600)),
        ):
            p = patch.object(updater, name, value)
            p.start()
            self.addCleanup(p.stop)

    def write_config(self):
        self.config.write_text(json.dumps(self.conf) + "\n")
        self.config.chmod(0o600)

    def publish_next(self):
        git("switch", "-c", "next", cwd=self.repo)
        (self.repo / "next.txt").write_text("new branch\n")
        git("add", "next.txt", cwd=self.repo)
        git("commit", "-m", "next ready", cwd=self.repo)
        git("push", "-u", "origin", "next", cwd=self.repo)
        git("switch", "main", cwd=self.repo)
        git("branch", "-D", "next", cwd=self.repo)

    def test_legacy_configuration_defaults_to_main(self):
        data, channel = updater.read_checkout_config()
        self.assertEqual(channel, "main")
        self.assertNotIn("channel", data)
        self.assertEqual(updater.checkout_from_config(), self.repo)
        self.assertEqual(updater.sync_checkout(self.repo), None)

    def test_switch_to_new_remote_branch_and_back_without_install(self):
        self.publish_next()
        before = self.config.read_bytes()
        with patch.object(updater, "update", side_effect=AssertionError("installed")):
            self.assertEqual(updater.switch_channel(self.repo, "next"), "switched")
            self.assertTrue((self.repo / "next.txt").exists())
            self.assertEqual(updater.read_checkout_config()[1], "next")
            self.assertEqual(updater.checkout_from_config(), self.repo)
            self.assertEqual(updater.sync_checkout(self.repo), None)
            self.assertEqual(updater.switch_channel(self.repo, "main"), "switched")
        self.assertEqual(git("branch", "--show-current", cwd=self.repo), "main")
        self.assertEqual(updater.read_checkout_config()[1], "main")
        self.assertEqual(updater.switch_channel(self.repo, "main"), "unchanged")
        self.assertNotEqual(self.config.read_bytes(), before)

    def test_missing_remote_next_never_changes_config_or_live_release(self):
        original = self.config.read_bytes()
        with patch.object(updater, "update", side_effect=AssertionError("installed")):
            with self.assertRaises(ValueError):
                updater.switch_channel(self.repo, "next")
        self.assertEqual(git("branch", "--show-current", cwd=self.repo), "main")
        self.assertEqual(self.config.read_bytes(), original)

    def test_drift_and_interrupted_journal_refuse_switch(self):
        self.publish_next()
        with patch.object(updater, "live_ok", return_value=False):
            with self.assertRaisesRegex(ValueError, "drift"):
                updater.switch_channel(self.repo, "next")
        with patch.object(updater, "read_journal", return_value={"phase": "prepared"}):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                updater.switch_channel(self.repo, "next")
        self.assertEqual(git("branch", "--show-current", cwd=self.repo), "main")

    def test_invalid_config_or_source_does_not_get_trusted(self):
        for channel in ("dev", "../next", "", None, 7):
            with self.subTest(channel=channel):
                self.conf["channel"] = channel
                self.write_config()
                with self.assertRaises(ValueError):
                    updater.read_checkout_config()
        self.conf["channel"] = "next"
        self.write_config()
        with self.assertRaisesRegex(ValueError, "branch"):
            updater.checkout_from_config()
        for extra in ({"unexpected": "field"},):
            self.conf = {"format": updater.FORMAT, "checkout": str(self.repo), **extra}
            self.write_config()
            with self.assertRaises(ValueError):
                updater.read_checkout_config()
        with self.assertRaises(ValueError):
            updater.switch_channel(self.repo, "unreviewed")


class ManifestAndCommandTests(unittest.TestCase):
    def test_current_release_chains_from_operator_accepted_baseline(self):
        obj = updater.manifest(ROOT)
        self.assertEqual(obj["format"], updater.FORMAT)
        self.assertEqual(obj["restart_manager"], obj["release"] not in
                         ("v0.8.0-shadow2", "v0.8.0-shadow3", "v0.8.0-shadow4",
                          "v0.8.0-chhttps1","v0.8.0-r3diag1",
                           "v0.8.0-r3format1", "v0.8.0-r3skip1",
                           "v0.8.0-r3canary1"))
        if obj["release"] == "v0.7.8-updater2":
            self.assertEqual(obj["from"], "v0.7.6-oc41-polish1")
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bobctl", "bob-release-updater", "bob_social_memory.py",
                              "bob-activity-manager", "navigation_shell.py"})
        elif obj["release"] == "v0.8.0-shadow1":
            self.assertEqual(obj["from"], "v0.7.8-updater2")
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob_v08_package.pyz", "bob-v08-shadow",
                              "bob-v08-activate", "bob-v08-experience", "bob_v08_bridge.py",
                              "bobctl", "bob-release-updater", "bob-activity-manager", "navigation_shell.py"})
        elif obj["release"] == "v0.8.0-shadow2":
            self.assertEqual(obj["from"], "v0.8.0-shadow1")
            self.assertFalse(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob_v08_package.pyz", "bob-v08-shadow"})
        elif obj["release"] == "v0.8.0-shadow3":
            self.assertEqual(obj["from"], "v0.8.0-shadow2")
            self.assertFalse(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob_v08_package.pyz", "bob-v08-shadow"})
        elif obj["release"] == "v0.8.0-shadow4":
            self.assertEqual(obj["from"], "v0.8.0-shadow3")
            self.assertFalse(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob_v08_package.pyz", "bob-v08-shadow"})
        elif obj["release"] == "v0.8.0-r3stage1":
            self.assertEqual(obj["from"], "v0.8.0-shadow4")
            self.assertTrue(obj["restart_manager"])
            # OFF-first R3: owner dashboard/proposal files only. No
            # credentialed publisher, timer, legacy Scout, auto switch or
            # live SQLite migration is part of this versioned code update.
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob_r3_package.pyz", "bob-r3-propose",
                              "bob_r313d_package.py", "bob_r313d_owner.py",
                              "bob_r313d_web.py", "bob-activity-manager",
                              "navigation_shell.py"})
            self.assertNotIn("bob-moltbook-publisher",
                             {i["name"] for i in obj["files"]})
        elif obj["release"] == "v0.8.0-chhttps1":
            self.assertEqual(obj["from"],"v0.8.0-r3stage1")
            self.assertFalse(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob-release-updater","bobctl"})
            self.assertNotIn("bob-activity-manager",
                             {i["name"] for i in obj["files"]})
            self.assertNotIn("bob-moltbook-publisher",
                             {i["name"] for i in obj["files"]})
        elif obj["release"] == "v0.8.0-chhttps3":
            self.assertEqual(obj["from"],"v0.8.0-chhttps1")
            self.assertTrue(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob_manager_tls.py","bob-activity-manager"})
            self.assertNotIn("bob-moltbook-publisher",
                             {i["name"] for i in obj["files"]})
            self.assertNotIn("bobctl", {i["name"] for i in obj["files"]})
        elif obj["release"] == "v0.8.0-cutover1":
            self.assertEqual(obj["from"],"v0.8.0-chhttps3")
            self.assertTrue(obj["restart_manager"])
            names={i["name"] for i in obj["files"]}
            self.assertEqual(len(names),12)
            self.assertIn("bob-activity-manager",names)
            self.assertIn("bob-moltbook-publisher",names)
            self.assertIn("bob_r3_package.pyz",names)
            self.assertIn("bob-release-updater",names)
            self.assertIn("bobctl",names)
            self.assertNotIn("bob-r3-publisher",names)
        elif obj["release"]=="v0.8.0-r3diag1":
            self.assertEqual(obj["from"],"v0.8.0-cutover1")
            self.assertFalse(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob-release-updater","bobctl","bob_r3_package.pyz"})
            self.assertNotIn("bob-activity-manager",
                             {i["name"] for i in obj["files"]})
            self.assertNotIn("bob-moltbook-publisher",
                             {i["name"] for i in obj["files"]})
        elif obj["release"]=="v0.8.0-r3format1":
            self.assertEqual(obj["from"],"v0.8.0-r3diag1")
            self.assertFalse(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob-release-updater","bobctl","bob_r3_package.pyz"})
            self.assertNotIn("bob-activity-manager",
                             {i["name"] for i in obj["files"]})
            self.assertNotIn("bob-moltbook-publisher",
                             {i["name"] for i in obj["files"]})
        elif obj["release"]=="v0.8.0-r3skip1":
            self.assertEqual(obj["from"],"v0.8.0-r3format1")
            self.assertFalse(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob-release-updater","bobctl","bob_r3_package.pyz"})
            self.assertNotIn("bob-activity-manager",
                             {i["name"] for i in obj["files"]})
            self.assertNotIn("bob-moltbook-publisher",
                             {i["name"] for i in obj["files"]})
        elif obj["release"]=="v0.8.0-r3canary1":
            self.assertEqual(obj["from"],"v0.8.0-r3skip1")
            self.assertFalse(obj["restart_manager"])
            self.assertEqual({i["name"] for i in obj["files"]},
                             {"bob-release-updater","bobctl","bob_r3_package.pyz",
                              "bob_r3_canary_lock.py","bob_r313c_adapter.py",
                              "bob-moltbook-publisher","bob-r3-canary-arm"})
            self.assertNotIn("bob-activity-manager",
                             {i["name"] for i in obj["files"]})
            self.assertNotIn("bob-moltbook-scout",
                             {i["name"] for i in obj["files"]})
        elif obj["release"]=="v0.8.0-autonomy1":
            self.assertEqual(obj["from"],"v0.8.0-r3canary1")
            self.assertTrue(obj["restart_manager"])
            reviewed=json.loads((ROOT/"releases/candidates/r4-autonomy1-consolidated.json").read_text())
            self.assertEqual(obj,reviewed)
            names={i["name"] for i in obj["files"]}
            self.assertEqual(len(names),23)
            self.assertIn("bob-activity-manager",names)
            self.assertIn("bob-moltbook-publisher",names)
            self.assertIn("bob-release-updater",names)
            self.assertIn("bobctl",names)
            self.assertIn("bob_r4_schema.py",names)
            self.assertIn("bob_r4_publisher_adapter.py",names)
            self.assertNotIn("bob-r4-publisher",names)
            self.assertNotIn("bob-moltbook-scout",names)
        elif obj["release"]=="v0.8.0-r4propose1":
            self.assertEqual(obj["from"],"v0.8.0-autonomy1")
            self.assertTrue(obj["restart_manager"])
            reviewed=json.loads((ROOT/"releases/candidates/r4-propose1-one-shot.json").read_text())
            self.assertEqual(obj,reviewed)
            names={i["name"] for i in obj["files"]}
            self.assertEqual(names,{"bob-release-updater","bobctl",
                                    "bob_r4_agent.py","bob_r4_installed_gate.py"})
            self.assertNotIn("bob-moltbook-publisher",names)
            self.assertNotIn("bob-r4-propose",names)
        else:
            self.fail("Unexpected release chain")
        for item in obj["files"]:
            output = updater.release_bytes(ROOT, item)
            self.assertTrue(output)
            if not item["name"].endswith(".pyz"):
                compile(output, item["name"], "exec")
        if obj["release"] == "v0.7.8-updater2":
            by_name = {item["name"]: item for item in obj["files"]}
            self.assertEqual(by_name["bob-activity-manager"]["builder"],
                             "scripts/build_v076_fm41_candidate.py")

    def test_v2_flat_compatible_manifest_validated_without_widening_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "releases").mkdir()
            v1 = updater.manifest(ROOT)
            v2 = dict(v1, format=updater.FORMAT_V2)
            location = folder / updater.MANIFEST
            location.write_text(json.dumps(v2))
            self.assertEqual(updater.manifest(folder)["format"], updater.FORMAT_V2)
            for rejected in (
                    dict(v2, migrations=[{"arbitrary": "code"}]),
                    dict(v2, files=[{"name": "credentials.json", "source": "src/bin/evil"}]),
                    dict(v2, files=[{"name": "bobctl", "source": "../../etc/passwd"}]),
                    dict(v2, format="bob-updater-v3")):
                with self.subTest(payload=str(rejected)[:100]):
                    location.write_text(json.dumps(rejected))
                    with self.assertRaises(ValueError):
                        updater.manifest(folder)

    def test_switch_command_cannot_reach_install_or_sync(self):
        with patch.object(updater.os, "geteuid", return_value=1000), \
             patch.object(updater, "checkout_from_config", return_value=Path("/tmp/mock-repo")), \
             patch.object(updater, "sync_checkout", side_effect=AssertionError("sync")), \
             patch.object(updater, "update", side_effect=AssertionError("install")), \
             patch.object(updater, "switch_channel", return_value="switched") as switch, \
             patch.object(sys, "argv", ["bob-release-updater", "--channel", "next"]), \
             patch.object(sys, "stdin", Mock(isatty=lambda: True)), \
             patch("builtins.input", return_value="SWITCH-NEXT"), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(updater.main(), 0)
        switch.assert_called_once_with(Path("/tmp/mock-repo"), "next")
        self.assertIn("no production changes", output.getvalue())

    def test_failed_chain_reports_safe_specific_versions_without_install(self):
        current = {"format": updater.FORMAT, "release": "v0.7.6-oc41-polish1",
                   "files": {}}
        plan = {"format": updater.FORMAT, "release": "v0.7.8-updater2",
                "from": "v0.7.7-fm41-social1", "files": [],
                "restart_manager": False, "notes": "fake"}
        with patch.object(updater.os, "geteuid", return_value=1000), \
             patch.object(updater, "checkout_from_config", return_value=Path("/tmp/mock")), \
             patch.object(updater, "sync_checkout", return_value=None), \
             patch.object(updater, "registry", return_value=current), \
             patch.object(updater, "manifest", return_value=plan), \
             patch.object(updater, "update", side_effect=AssertionError("install")), \
             patch.object(sys, "argv", ["bob-release-updater"]), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(updater.main(), 1)
        self.assertIn("Reason: release chain mismatch: installed v0.7.6-oc41-polish1",
                      output.getvalue())
        self.assertIn("expected v0.7.7-fm41-social1", output.getvalue())

    def test_failed_channel_approval_does_not_run_switch(self):
        with patch.object(updater.os, "geteuid", return_value=1000), \
             patch.object(updater, "checkout_from_config", return_value=Path("/tmp/mock-repo")), \
             patch.object(updater, "switch_channel",
                          side_effect=AssertionError("must not run")), \
             patch.object(sys, "argv", ["bob-release-updater", "--channel", "next"]), \
             patch.object(sys, "stdin", Mock(isatty=lambda: True)), \
             patch("builtins.input", return_value="UPDATE"), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(updater.main(), 1)
        self.assertIn("REFUSED", output.getvalue())


if __name__ == "__main__":
    unittest.main()
