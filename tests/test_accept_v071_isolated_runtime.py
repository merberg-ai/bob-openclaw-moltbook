"""Tests for isolated v0.7.1 acceptance orchestrator."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts/accept_v071_isolated_runtime.py"
spec = importlib.util.spec_from_file_location("v071_runtime_gate", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Process:
    def __init__(self, code, stdout):
        self.returncode = code
        self.stdout = stdout

class RuntimeGateTests(unittest.TestCase):
    def test_both_checks_pass(self):
        index = [0]
        def fake(args, **kwargs):
            target = mod.SCRIPTS[index[0]][2]
            index[0] += 1
            self.assertTrue(kwargs["capture_output"])
            self.assertTrue(kwargs["timeout"] <= 45)
            return Process(0, target)
        self.assertEqual(mod.execute(runner=fake),
                         {"installed_layout": True, "browser_runtime": True})

    def test_stop_after_staging_failure(self):
        calls = []
        def fail(args, **kwargs):
            calls.append(args)
            return Process(1, mod.SCRIPTS[0][2])
        self.assertEqual(mod.execute(runner=fail), {"installed_layout": False})
        self.assertEqual(len(calls), 1)

    def test_marker_missing_refuses_even_zero_exit(self):
        self.assertEqual(mod.execute(runner=lambda *a, **kw: Process(0, "no marker")),
                         {"installed_layout": False})

    def test_timeout_refuses(self):
        import subprocess
        def timeout(args, **kw):
            raise subprocess.TimeoutExpired(args, kw["timeout"])
        self.assertEqual(mod.execute(runner=timeout), {"installed_layout": False})

if __name__ == "__main__":
    unittest.main()
