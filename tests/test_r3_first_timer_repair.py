"""Offline structural check of R3 first-run timer configuration."""
import unittest
from pathlib import Path

class TimerTest(unittest.TestCase):
    def test_seed(self):
        source=Path("scripts/repair_r3_first_timer.py").read_text()
        self.assertIn("OnActiveSec=2min",source)
        self.assertIn("--check",source)

if __name__=="__main__":
    unittest.main()
