"""Offline tests for mock-only child-process crash and rollback behavior."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stage_service_graph as stage
import rehearse_inert_process_lifecycle as lifecycle


class InertProcessLifecycleTests(unittest.TestCase):
    def test_complete_lifecycle_records_synthetic_restart_and_rollback(self):
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as d:
            root = Path(d)
            stage.create(root)
            result = lifecycle.exercise(root)
            self.assertEqual(result["mock_long_running_starts"], 7)
            self.assertTrue(result["crash_observed"])
            self.assertTrue(result["mock_restart_verified"])
            self.assertTrue(result["candidate_switch_verified"])
            self.assertTrue(result["rollback_restart_verified"])
            self.assertTrue(result["children_reaped"])
            self.assertFalse(result["live_install_modified"])
            rows = lifecycle.event_rows(root)
            self.assertEqual(len(rows), 7)
            self.assertEqual(sum(release == "candidate" for _,release in rows),2)

    def test_refuses_nonmock_role_without_process_launch(self):
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as d:
            root=Path(d)
            stage.create(root)
            with patch.object(lifecycle.subprocess, "Popen") as popen:
                with self.assertRaisesRegex(ValueError,"Only inert"):
                    lifecycle.start_mock(root,"live-moltbook-publisher")
                popen.assert_not_called()

    def test_modified_offline_config_blocks_process_spawn(self):
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as d:
            root=Path(d)
            stage.create(root)
            config=root/"private/MOCK-CONFIG.json"
            values=json.loads(config.read_text())
            values["allow_publish"]=True
            config.write_text(json.dumps(values))
            config.chmod(0o600)
            with patch.object(lifecycle.subprocess,"Popen") as popen:
                with self.assertRaisesRegex(ValueError,"offline dummy"):
                    lifecycle.start_mock(root,"gateway")
                popen.assert_not_called()

    def test_tampered_actor_source_blocks_process_spawn(self):
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as d:
            root=Path(d)
            stage.create(root)
            actor=root/"current/bin/stage_mock_actor.py"
            actor.write_bytes(actor.read_bytes()+b"\n# tampered\n")
            with patch.object(lifecycle.subprocess,"Popen") as popen:
                with self.assertRaisesRegex(ValueError,"changed"):
                    lifecycle.start_mock(root,"gateway")
                popen.assert_not_called()

    def test_mock_spawn_has_private_environment_and_own_session(self):
        with tempfile.TemporaryDirectory(prefix=stage.PREFIX) as d:
            root=Path(d)
            stage.create(root)
            class Stub:
                pass
            with patch.object(lifecycle.subprocess,"Popen",return_value=Stub()) as popen:
                lifecycle.start_mock(root,"manager")
                args=popen.call_args.args[0]
                kwargs=popen.call_args.kwargs
                self.assertEqual(args[0],sys.executable)
                self.assertEqual(args[args.index("--role")+1],"manager")
                self.assertEqual(args[-1],"--serve")
                self.assertTrue(kwargs["start_new_session"])
                self.assertEqual(kwargs["env"]["HOME"],str(root/"private"))
                self.assertNotIn("BOB_TOKEN",kwargs["env"])
                self.assertEqual(kwargs["cwd"],root)

    def test_reaper_handles_already_exited_process(self):
        class Finished:
            returncode=0
            pid=99999999
            def poll(self): return 0
            def wait(self,timeout): return 0
        with patch.object(lifecycle.os,"killpg") as kill:
            lifecycle.reap(Finished())
            kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
