"""Import-only structural safety checks for R3 first-run timer repair."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import r3_service_handoff as handoff
import repair_r3_first_timer as bootstrap

class TimerTest(unittest.TestCase):
    def test_seed_preserves_original_unit(self):
        self.assertEqual(bootstrap.BODY,b"[Timer]\\nOnActiveSec=2min\\n")
        self.assertNotIn("OnActiveSec",handoff.UNIT_TEXT[handoff.TIMER])
        self.assertIn("OnUnitInactiveSec=35min",handoff.UNIT_TEXT[handoff.TIMER])
        self.assertEqual(bootstrap.F.parent,bootstrap.D)

    def test_no_new_moltbook_publisher_unit_or_credential_target(self):
        self.assertEqual(
            {handoff.SERVICE,handoff.TIMER},
            set(handoff.UNIT_TEXT))
        self.assertNotIn("bob-moltbook-publisher",str(bootstrap.F))
        self.assertEqual(bootstrap.F.name,"10-first-run.conf")

if __name__=="__main__":
    unittest.main()
