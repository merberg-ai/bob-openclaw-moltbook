"""No real Moltbook calls: exact compiled one-run manual canary contract."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"/"lib"/"bob"))
from bob_r3_canary_lock import CanaryPin,PIN,matches_pin,still_pinned_for_send

RUN="20261101T040000Z"
TARGET="11111111-1111-4111-8111-111111111111"
SEAL="a"*64
NOW=datetime(2026,11,1,4,30,tzinfo=timezone.utc)
PINNED=CanaryPin(RUN,SEAL,TARGET,"2026-11-01T05:00:00Z")


def allowed(pin=PINNED, **updates):
    values=dict(run=RUN,seal=SEAL,target=TARGET,now=NOW,
                mode="manual",proposal_state="queued",queue_state="queued",
                attempted_at=None,approval=(SEAL,"approved"))
    values.update(updates)
    return matches_pin(pin,**values)


class CanaryPinTests(unittest.TestCase):
    def test_off_source_pin_cannot_authorize_any_run(self):
        self.assertEqual(PIN,CanaryPin())
        self.assertFalse(allowed(PIN))
        self.assertFalse(still_pinned_for_send(RUN,TARGET,NOW))

    def test_one_valid_sealed_owner_queued_run_only(self):
        self.assertTrue(allowed())
        for values in (
            {"run":"20261101T040001Z"},
            {"seal":"b"*64},
            {"target":"22222222-2222-4222-8222-222222222222"},
            {"mode":"auto"},
            {"proposal_state":"proposed"},
            {"queue_state":"uncertain"},
            {"attempted_at":"2026-11-01T04:29:00Z"},
            {"approval":None},
            {"approval":(SEAL,"rejected")},
            {"now":NOW+timedelta(hours=2)},
            {"now":NOW-timedelta(hours=1)},
        ):
            with self.subTest(values=values):
                self.assertFalse(allowed(**values))

    def test_malformed_or_overlong_pin_refused(self):
        self.assertFalse(allowed(CanaryPin(RUN,SEAL,TARGET,"not-a-date")))
        self.assertFalse(allowed(CanaryPin("bad",SEAL,TARGET,
                                          "2026-11-01T05:00:00Z")))
        self.assertFalse(allowed(CanaryPin(RUN,SEAL,TARGET,
                                          "2026-11-09T05:00:00Z")))


if __name__=="__main__":
    unittest.main()
