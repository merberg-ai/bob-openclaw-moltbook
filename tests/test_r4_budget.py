"""R4 cross-publisher attempt accounting: default conservative, fail closed."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_budget as budget

NOW=datetime(2026,11,1,16,20,tzinfo=timezone.utc)


class R4CountedBudgetTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        self.addCleanup(self.db.close)
        self.db.executescript("""
          CREATE TABLE r4_action_outbox(attempted_at TEXT);
          CREATE TABLE publish_jobs(attempted_at TEXT);
          CREATE TABLE original_posts(attempted_at TEXT);
        """)

    def add(self,table,at):
        self.db.execute("INSERT INTO "+table+" VALUES(?)",(at,))

    def test_initial_clear_and_old_day_does_not_count(self):
        self.assertTrue(budget.inspect(self.db,at=NOW).allowed)
        self.add("publish_jobs","2026-10-31T09:00:00Z")
        self.assertTrue(budget.inspect(self.db,at=NOW).allowed)

    def test_cross_publisher_cooldown_counts_legacy_and_original(self):
        self.add("publish_jobs",(NOW-timedelta(minutes=1)).isoformat())
        found=budget.inspect(self.db,at=NOW)
        self.assertFalse(found.allowed)
        self.assertEqual(found.reason,"r4_global_counted_cooldown")
        self.db.execute("DELETE FROM publish_jobs")
        self.add("original_posts",(NOW-timedelta(minutes=10)).isoformat())
        self.assertEqual(budget.inspect(self.db,at=NOW).reason,
                         "r4_global_counted_cooldown")
        self.assertTrue(budget.inspect(self.db,at=NOW+timedelta(minutes=25)).allowed)

    def test_global_daily_cap_counts_unknown_and_failed_attempts(self):
        for i,table in enumerate(
                ("r4_action_outbox","publish_jobs","original_posts",
                 "r4_action_outbox")):
            self.add(table,(NOW-timedelta(hours=i+1)).isoformat())
        found=budget.inspect(self.db,at=NOW)
        self.assertFalse(found.allowed)
        self.assertEqual(found.reason,"r4_global_counted_daily_cap")
        self.assertEqual(found.used_today,4)

    def test_corrupt_future_or_timezone_free_history_blocks(self):
        for sample,reason in (("invalid","malformed_attempt_history"),
                              ("2026-11-01T16:19:00","untrusted_attempt_timezone"),
                              ("2026-11-01T16:21:00Z","attempt_clock_future")):
            with self.subTest(sample=sample):
                self.add("r4_action_outbox",sample)
                self.assertEqual(budget.inspect(self.db,at=NOW).reason,reason)
                self.db.execute("DELETE FROM r4_action_outbox")

    def test_missing_required_table_holds_r4(self):
        self.db.execute("DROP TABLE publish_jobs")
        self.assertEqual(budget.inspect(self.db,at=NOW).reason,
                         "required_attempt_ledger_unavailable")

    def test_bounds_apply_only_to_counted_events_not_queued_ones(self):
        self.add("publish_jobs",None)
        self.assertTrue(budget.inspect(self.db,at=NOW).allowed)


if __name__=="__main__":
    unittest.main()
