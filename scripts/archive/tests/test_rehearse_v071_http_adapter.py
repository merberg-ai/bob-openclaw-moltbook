"""Offline tests for isolated real HTTP service lifecycle."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts/rehearse_v071_http_adapter.py"
spec = importlib.util.spec_from_file_location("v071_http_adapter", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class AdapterTests(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(mod.exercise("healthy"), ("candidate_healthy", 1))
    def test_failed_health_recovers(self):
        self.assertEqual(mod.exercise("failed-health"), ("rolled_back", 2))
    def test_failed_recovery_reported(self):
        self.assertEqual(mod.exercise("failed-recovery"), ("recovery_failed", 2))
    def test_stopped_server_is_not_healthy(self):
        srv = mod.IsolatedService()
        self.assertFalse(srv.probe())
    def test_start_budget_enforced(self):
        srv = mod.IsolatedService()
        try:
            srv.start()
            with self.assertRaises(ValueError):
                srv.start()
            srv.stop()
            srv.start()
            srv.stop()
            with self.assertRaises(ValueError):
                srv.start()
        finally:
            srv.stop()
    def test_unhealthy_http_response_refused(self):
        srv = mod.IsolatedService(healthy=False)
        try:
            srv.start()
            self.assertFalse(srv.probe())
        finally:
            srv.stop()
    def test_invalid_probe_budget(self):
        with self.assertRaises(ValueError):
            mod.bounded_health(mod.IsolatedService(), attempts=3)

if __name__ == "__main__":
    unittest.main()
