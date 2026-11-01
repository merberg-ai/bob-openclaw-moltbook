"""Exact one-run R3 canary owner-arm and source pin, no real Moltbook calls."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src/lib/bob"),str(ROOT/"src")]
import bob_r3_canary_lock as lock
import bob_r313c_adapter as adapter

NOW=datetime(2026,11,2,2,30,tzinfo=timezone.utc)


def allowed(**updates):
    values=dict(run=lock.PIN.run,seal=lock.PIN.seal,target=lock.PIN.target,
                now=NOW,mode="manual",proposal_state="queued",
                queue_state="queued",attempted_at=None,
                approval=(lock.PIN.seal,"approved"))
    values.update(updates)
    return lock.matches_pin(lock.PIN,**values)


class R3ExactCanaryPinTests(unittest.TestCase):
    def test_immutable_compiled_owner_approved_scope(self):
        self.assertEqual(lock.PIN.run,"20261101T151033Z")
        self.assertEqual(lock.PIN.seal,
            "870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2")
        self.assertEqual(lock.PIN.target,"bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a")
        self.assertEqual(lock.PIN.expires_utc,"2026-11-05T00:00:00Z")
        self.assertTrue(allowed())
        self.assertFalse(adapter.R313C_REAL_DISPATCH)
        self.assertFalse(adapter.R312_REAL_DISPATCH)
        self.assertTrue(adapter.R3_EXACT_CANARY_COMPILED)

    def test_one_seal_one_source_one_target_manual_queue_only(self):
        for value in (
            {"run":"20261101T151034Z"},
            {"seal":"1"*64},
            {"target":"aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"},
            {"mode":"auto"},
            {"proposal_state":"proposed"},
            {"queue_state":"uncertain"},
            {"attempted_at":"2026-11-02T02:00:00Z"},
            {"approval":None},
            {"approval":(lock.PIN.seal,"rejected")},
            {"now":NOW-timedelta(days=2)},
            {"now":NOW+timedelta(days=4)},
        ):
            with self.subTest(value=value):
                self.assertFalse(allowed(**value))

    def test_install_and_queue_without_explicit_arm_still_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            (home/".config/bob-system").mkdir(parents=True,mode=0o700)
            with patch.object(lock.Path,"home",return_value=home):
                self.assertFalse(lock.marker_valid(now=NOW))
                self.assertFalse(lock.still_pinned_for_send(
                    lock.PIN.run,lock.PIN.target,NOW))
                self.assertFalse(adapter.production_dispatch_enabled())

    def test_exact_owner_marker_is_private_and_expires(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            folder=home/".config/bob-system"
            folder.mkdir(mode=0o700,parents=True)
            marker=folder/lock.ARM_NAME
            with patch.object(lock.Path,"home",return_value=home):
                marker.write_text(json.dumps(lock.expected_marker()))
                marker.chmod(0o600)
                self.assertTrue(lock.marker_valid(now=NOW))
                self.assertTrue(lock.still_pinned_for_send(
                    lock.PIN.run,lock.PIN.target,NOW))
                self.assertTrue(adapter.production_dispatch_enabled())
                self.assertFalse(lock.marker_valid(now=NOW+timedelta(days=6)))
                marker.chmod(0o644)
                self.assertFalse(lock.marker_valid(now=NOW))
                marker.chmod(0o600)
                marker.write_text(json.dumps(dict(lock.expected_marker(),
                                                   run="20261101T151034Z")))
                self.assertFalse(lock.marker_valid(now=NOW))

    def test_malformed_pin_never_matches(self):
        invalid=lock.CanaryPin(run="wrong",seal=lock.PIN.seal,
                               target=lock.PIN.target,
                               expires_utc=lock.PIN.expires_utc)
        self.assertFalse(lock.matches_pin(
            invalid,run=lock.PIN.run,seal=lock.PIN.seal,target=lock.PIN.target,
            now=NOW,mode="manual",proposal_state="queued",
            queue_state="queued",attempted_at=None,
            approval=(lock.PIN.seal,"approved")))


if __name__=="__main__":
    unittest.main()
