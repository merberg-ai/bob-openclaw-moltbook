"""Offline preflight tests. systemd manager never contacted during test."""
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import preflight_stage_systemd_manager as preflight


def fake_result(stdout: str, returncode: int = 0):
    return subprocess.CompletedProcess(["systemctl"], returncode, stdout, "")


def good_query(args: list[str]):
    if args == ["systemctl", "--user", "show", "--property=Version", "--no-pager"]:
        return fake_result("Version=257\n")
    return fake_result("LoadState=not-found\nActiveState=inactive\nUnitFileState=\n")


class StageManagerPreflightTests(unittest.TestCase):
    def test_all_twenty_scope_qualified_units_absent(self):
        with patch.object(preflight.shutil, "which", return_value="/bin/synthetic"):
            state = preflight.query_preflight(run=good_query)
        self.assertTrue(state["ready_for_separate_stage_execution_review"])
        self.assertTrue(state["unique_stage_names_only"])
        self.assertEqual(state["stage_unit_names_checked"], 20)
        self.assertEqual(state["colliding_or_reserved_names"], 0)
        self.assertEqual(state["unavailable_name_queries"], 0)
        self.assertFalse(state["live_install_modified"])

    def test_any_existing_service_blocks(self):
        def query(args):
            if "bob-v070-stage-gateway.service" in args and "--user" in args:
                return fake_result("LoadState=loaded\nActiveState=inactive\nUnitFileState=disabled\n")
            return good_query(args)
        with patch.object(preflight.shutil, "which", return_value="/bin/synthetic"):
            state = preflight.query_preflight(run=query)
        self.assertEqual(state["colliding_or_reserved_names"], 1)
        self.assertFalse(state["ready_for_separate_stage_execution_review"])

    def test_unavailable_system_scope_does_not_pass(self):
        def query(args):
            if "--system" in args:
                return None
            return good_query(args)
        with patch.object(preflight.shutil, "which", return_value="/bin/synthetic"):
            state = preflight.query_preflight(run=query)
        self.assertEqual(state["unavailable_name_queries"], 10)
        self.assertFalse(state["ready_for_separate_stage_execution_review"])

    def test_failed_manager_probe_does_not_pass(self):
        def query(args):
            if args == ["systemctl", "--user", "show", "--property=Version", "--no-pager"]:
                return fake_result("", returncode=1)
            return good_query(args)
        with patch.object(preflight.shutil, "which", return_value="/bin/synthetic"):
            state = preflight.query_preflight(run=query)
        self.assertFalse(state["user_systemd_manager_reachable"])
        self.assertFalse(state["ready_for_separate_stage_execution_review"])

    def test_missing_systemd_run_blocks_future_gate(self):
        with patch.object(preflight.shutil, "which", side_effect=lambda x: None if x == "systemd-run" else "/bin/synthetic"):
            state = preflight.query_preflight(run=good_query)
        self.assertFalse(state["required_tools_detected"])
        self.assertFalse(state["ready_for_separate_stage_execution_review"])

    def test_only_fixed_readonly_commands_accepted(self):
        for argv in (
            ["systemctl", "--user", "start", "bob-v070-stage-gateway.service"],
            ["systemctl", "--user", "daemon-reload"],
            ["systemctl", "--user", "show", "openclaw-gateway.service", "--property=ActiveState", "--no-pager"],
            ["systemd-run", "--user", "/bin/true"],
        ):
            with self.subTest(argv=argv):
                with patch.object(preflight.subprocess, "run") as call:
                    with self.assertRaises(ValueError):
                        preflight.safe_query(argv)
                    call.assert_not_called()

    def test_systemctl_call_cannot_execute_shell(self):
        argv = ["systemctl", "--user", "show",
                "bob-v070-stage-manager.service",
                "--property=LoadState,ActiveState,UnitFileState", "--no-pager"]
        with patch.object(preflight.subprocess, "run", return_value=fake_result(
                "LoadState=not-found\nActiveState=inactive\nUnitFileState=\n")) as call:
            preflight.safe_query(argv)
        self.assertEqual(call.call_args.args[0], argv)
        self.assertNotIn("shell", call.call_args.kwargs)
        self.assertEqual(call.call_args.kwargs["timeout"], 4)


if __name__ == "__main__":
    unittest.main()
