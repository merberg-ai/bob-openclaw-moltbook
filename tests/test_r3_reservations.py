"""R3.1 completely offline SQLite reservation race/crash/policy simulations."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bob_v08.core import Action, Observation, Policy, PolicyState
from bob_v08.r3_reservations import SimulationLedger

RUN = "20261030T200610Z"
TARGET = "a9ccf436-c5d5-4849-af92-843670ab8271"
OTHER = "bf5b5b62-8a42-4f58-b139-4157b7bfa642"
HASH = "a" * 64
BEFORE = datetime(2026, 10, 30, 23, 59, 40, tzinfo=timezone.utc)


def candidate(target=TARGET, run=RUN, text="A source-bound technical comment."):
    obs = Observation(run, target, "Agent", "Example", "Source data", HASH,
                      "b" * 64, BEFORE.isoformat())
    return Action("comment", run, target, "Interesting technical discussion.", text), obs


def policy(*, budget=3, spacing=0, paused=False, shadow=False, dial="auto"):
    return replace(Policy(), dials={"comment": dial}, budgets={"comment": budget},
                   minimum_spacing={"comment": spacing}, paused=paused, shadow=shadow)


class ReservationLabTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ledger = SimulationLedger(self.root / "simulation.sqlite3")
        self.action, self.observed = candidate()
        self.current = PolicyState(BEFORE)

    def reserve(self, **kwargs):
        return self.ledger.simulate_reserve(
            self.action, self.observed, kwargs.pop("policy", policy()),
            kwargs.pop("state", self.current),
            auto_enabled=kwargs.pop("auto_enabled", True))

    def preflight(self, token, **kwargs):
        return self.ledger.simulate_pre_send(
            token, self.action, self.observed,
            kwargs.pop("policy", policy()),
            kwargs.pop("state", self.current),
            auto_enabled=kwargs.pop("auto_enabled", True))

    def test_default_policy_and_owner_auto_flag_deny_without_reservation(self):
        for p, enabled, expected in (
                (Policy(), True, "shadow_only"),
                (policy(dial="off"), True, "comment_not_auto"),
                (policy(dial="propose"), True, "comment_not_auto"),
                (policy(), False, "legacy_auto_disabled"),
                (policy(paused=True), True, "global_pause"),
                (policy(budget=0), True, "daily_budget")):
            with self.subTest(reason=expected):
                outcome = self.reserve(policy=p, auto_enabled=enabled)
                self.assertEqual(outcome.state, "refused")
                self.assertEqual(outcome.reason, expected)
                self.assertFalse(outcome.acted)
                self.assertTrue(outcome.simulated)

    def test_two_step_simulated_intent_never_grants_dispatch(self):
        reserve = self.reserve()
        self.assertEqual(reserve.state, "reserved")
        self.assertEqual(len(reserve.token), 32)
        self.assertFalse(reserve.acted)
        preview = self.preflight(reserve.token)
        self.assertEqual(preview.state, "intent_simulated")
        self.assertEqual(preview.reason, "within_policy")
        self.assertFalse(preview.acted)
        self.assertTrue(preview.simulated)
        self.assertEqual(self.preflight(reserve.token).reason, "reservation_not_pending")
        with sqlite3.connect(self.ledger.path) as db:
            states = db.execute("SELECT state FROM reservations").fetchall()
            self.assertEqual(states, [("intent_simulated",)])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM changes").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master "
                                        "WHERE type='table' AND name='publish_jobs'").fetchone()[0], 0)
        self.assertEqual(self.ledger.path.stat().st_mode & 0o077, 0)

    def test_exact_content_and_snapshot_revalidated_at_pre_send(self):
        first = self.reserve()
        bad_action = replace(self.action, text="Changed after approval.")
        invalid = self.ledger.simulate_pre_send(
            first.token, bad_action, self.observed, policy(), self.current, auto_enabled=True)
        self.assertEqual((invalid.state, invalid.reason),
                         ("held", "reservation_source_changed"))
        self.assertEqual(self.preflight(first.token).reason, "reservation_not_pending")
        self.assertEqual(self.reserve().reason, "duplicate_target")

    def test_owner_revocation_and_pause_after_reservation_hold_permanently(self):
        cases = (
            (policy(paused=True), True, "global_pause"),
            (policy(dial="off"), True, "comment_not_auto"),
            (policy(), False, "legacy_auto_disabled"),
        )
        for i, (changed, flag, expected) in enumerate(cases):
            with self.subTest(reason=expected):
                action, obs = candidate(target=[
                    TARGET, OTHER, "11111111-1111-4111-8111-111111111111"][i],
                    run=["20261030T200610Z", "20261030T200611Z", "20261030T200612Z"][i])
                accepted = self.ledger.simulate_reserve(
                    action, obs, policy(), self.current, auto_enabled=True)
                self.assertEqual(accepted.state, "reserved")
                result = self.ledger.simulate_pre_send(
                    accepted.token, action, obs, changed, self.current,
                    auto_enabled=flag)
                self.assertEqual((result.state, result.reason), ("held", expected))
                self.assertEqual(self.ledger.simulate_pre_send(
                    accepted.token, action, obs, policy(), self.current,
                    auto_enabled=True).reason, "reservation_not_pending")

    def test_concurrent_same_target_has_exactly_one_winner(self):
        def job(i):
            a, o = candidate(run=f"20261030T2006{i:02d}Z")
            return self.ledger.simulate_reserve(
                a, o, policy(budget=5), self.current, auto_enabled=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(job, (13, 14)))
        self.assertEqual(sorted(x.state for x in results), ["refused", "reserved"])
        self.assertEqual([x.reason for x in results if x.state == "refused"],
                         ["duplicate_target"])
        with sqlite3.connect(self.ledger.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0], 1)

    def test_budget_counts_concurrent_reservations_even_without_send(self):
        a1, o1 = candidate()
        a2, o2 = candidate(OTHER, "20261030T200611Z")
        first = self.ledger.simulate_reserve(
            a1, o1, policy(budget=1), self.current, auto_enabled=True)
        self.assertEqual(first.state, "reserved")
        second = self.ledger.simulate_reserve(
            a2, o2, policy(budget=1), self.current, auto_enabled=True)
        self.assertEqual((second.state, second.reason), ("refused", "daily_budget"))
        self.assertEqual(self.ledger.simulate_pre_send(
            first.token, a1, o1, policy(budget=1), self.current,
            auto_enabled=True).state, "intent_simulated")

    def test_utc_rollover_and_minimum_spacing_are_independent(self):
        first = self.reserve(policy=policy(budget=1, spacing=30))
        self.assertEqual(first.state, "reserved")
        action2, obs2 = candidate(OTHER, "20261030T200611Z")
        state = PolicyState(BEFORE + timedelta(minutes=1))
        next_day = self.ledger.simulate_reserve(
            action2, obs2, policy(budget=1, spacing=30), state, auto_enabled=True)
        self.assertEqual((next_day.state, next_day.reason),
                         ("refused", "minimum_spacing"))
        far = PolicyState(BEFORE + timedelta(minutes=31))
        accepted = self.ledger.simulate_reserve(
            action2, obs2, policy(budget=1, spacing=30), far, auto_enabled=True)
        self.assertEqual(accepted.state, "reserved")

    def test_external_legacy_counts_and_duplicate_target_fail_closed(self):
        prior = PolicyState(BEFORE, counts={"comment": 2},
                            addressed=frozenset({("comment", OTHER)}))
        self.assertEqual(self.reserve(policy=policy(budget=2), state=prior).reason,
                         "daily_budget")
        action2, obs2 = candidate(OTHER, "20261030T200611Z")
        refused = self.ledger.simulate_reserve(
            action2, obs2, policy(), prior, auto_enabled=True)
        self.assertEqual((refused.state, refused.reason),
                         ("refused", "duplicate_target"))
        self.assertEqual(self.reserve(state=PolicyState(BEFORE, counts={"comment": -1})).reason,
                         "invalid_baseline_counts")

    def test_unknown_outcome_is_irreversible_and_never_retried(self):
        first = self.reserve()
        self.assertEqual(self.preflight(first.token).state, "intent_simulated")
        uncertain = self.ledger.simulate_uncertain(first.token, BEFORE)
        self.assertEqual((uncertain.state, uncertain.reason),
                         ("uncertain_simulated", "synthetic_unknown_outcome"))
        self.assertEqual(self.ledger.simulate_uncertain(first.token, BEFORE).state,
                         "refused")
        self.assertEqual(self.reserve().reason, "duplicate_target")

    def test_roll_back_transaction_on_failed_audit_insert(self):
        # Any failure after reservation insertion must roll back both rows.
        self.assertEqual(self.reserve(policy=policy(dial="off")).state, "refused")
        with sqlite3.connect(self.ledger.path) as db:
            db.execute("CREATE TRIGGER fail_log BEFORE INSERT ON changes "
                       "BEGIN SELECT RAISE(ABORT,'test synthetic crash'); END")
        with self.assertRaisesRegex(sqlite3.DatabaseError, "synthetic crash"):
            self.reserve()
        with sqlite3.connect(self.ledger.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0], 0)
            db.execute("DROP TRIGGER fail_log")
        self.assertEqual(self.reserve().state, "reserved")

    def test_untrusted_action_or_database_path_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_reservation_action"):
            self.ledger.simulate_reserve(
                replace(self.action, target_id=OTHER), self.observed, policy(),
                self.current, auto_enabled=True)
        with self.assertRaisesRegex(ValueError, "unsupported_reservation_action"):
            self.ledger.simulate_reserve(
                replace(self.action, kind="skip", text=""), self.observed, policy(),
                self.current, auto_enabled=True)
        bad_source = replace(self.observed, snapshot_sha256="not a hash")
        with self.assertRaisesRegex(ValueError, "unverified_source"):
            self.ledger.simulate_reserve(
                self.action, bad_source, policy(), self.current, auto_enabled=True)
        link = self.root / "linked.sqlite3"
        link.symlink_to(self.root / "not-created.sqlite3")
        with self.assertRaisesRegex(ValueError, "unsafe_simulation_database"):
            SimulationLedger(link).simulate_reserve(
                self.action, self.observed, policy(), self.current, auto_enabled=True)
        self.assertFalse((self.root / "not-created.sqlite3").exists())

    def test_no_external_publish_or_host_policy_mutation(self):
        import inspect
        import bob_v08.r3_reservations as engine
        source = inspect.getsource(engine)
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("api_key(", source)
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("publish_jobs", source)
        self.assertNotIn("network", inspect.signature(
            engine.SimulationLedger.simulate_reserve).parameters)


if __name__ == "__main__":
    unittest.main()
