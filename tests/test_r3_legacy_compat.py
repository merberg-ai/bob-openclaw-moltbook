"""R3.2 offline v0.7 compatibility tests. Synthetic database ONLY."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bob_v08.core import Action, Observation
from bob_v08.r3_legacy_compat import LegacyCompatLab, LAB_MARKER

WHEN = datetime(2026, 10, 30, 23, 30, tzinfo=timezone.utc)
RUN_MANUAL = "20261030T230000Z"
RUN_AUTO = "20261030T231000Z"
PID_MANUAL = "a9ccf436-c5d5-4849-af92-843670ab8271"
PID_AUTO = "31ca4dd9-a0b4-4991-a671-f063946e1123"
SHA = "a" * 64
TEXT_MANUAL = "This is a careful, source-linked technical observation."
TEXT_AUTO = "This is a separate, freshly reviewed, technical comment."


def candidate(run, target, draft):
    obs = Observation(run, target, "Other agent", "A relevant post",
                      "Example third-party content", "b" * 64, SHA, WHEN.isoformat())
    action = Action("comment", run, target, "A relevant technical discussion.", draft)
    return action, obs


def create_fixture(path):
    path.parent.mkdir(mode=0o700)
    with sqlite3.connect(path) as db:
        # Exact v0.7 baseline columns and constraints from bob_publish_common.connect()
        db.executescript("""
        CREATE TABLE decisions (
            run_id TEXT PRIMARY KEY, draft_sha256 TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('approved','rejected')),
            decided_at TEXT NOT NULL
        );
        CREATE TABLE publish_settings (name TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE publish_jobs (
            run_id TEXT PRIMARY KEY, approval_sha256 TEXT NOT NULL,
            post_id TEXT NOT NULL, draft_comment TEXT NOT NULL,
            mode TEXT NOT NULL CHECK(mode IN ('manual','auto')),
            state TEXT NOT NULL, created_at TEXT NOT NULL, attempted_at TEXT,
            comment_id TEXT, challenge_code TEXT, challenge_text TEXT,
            challenge_expires_at TEXT, verify_answer TEXT, last_error TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE r3_lab_meta (name TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE r3_lab_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL,
            kind TEXT NOT NULL,transition TEXT NOT NULL,at_utc TEXT NOT NULL
        );""")
        db.execute("INSERT INTO r3_lab_meta VALUES('contract',?)", (LAB_MARKER,))
        db.executemany("INSERT INTO publish_settings VALUES(?,?)", [
            ("auto_enabled", "1"), ("activity_limit_comment_daily", "2"),
            ("activity_limit_comment_auto_daily", "1"),
            ("activity_limit_comment_gap_minutes", "0")])
        # 0 spacing is not allowed by the real policy, so override to safe min.
        db.execute("UPDATE publish_settings SET value='10' "
                   "WHERE name='activity_limit_comment_gap_minutes'")
    os.chmod(path, 0o600)


class CompatTests(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.folder = Path(root.name) / "r3-compat-fixtures"
        self.file = self.folder / "r3-legacy-compat-lab.sqlite3"
        create_fixture(self.file)
        self.lab = LegacyCompatLab(self.file)
        self.manual, self.manual_obs = candidate(
            RUN_MANUAL, PID_MANUAL, TEXT_MANUAL)
        self.auto, self.auto_obs = candidate(
            RUN_AUTO, PID_AUTO, TEXT_AUTO)

    def job(self, action, *, mode="manual", state="queued",
            attempted_at=None, created=None):
        now = created or WHEN.isoformat()
        with sqlite3.connect(self.file) as db:
            db.execute(
                "INSERT INTO publish_jobs(run_id,approval_sha256,post_id,draft_comment,"
                "mode,state,created_at,attempted_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (action.source_run, SHA, action.target_id, action.text,
                 mode, state, now, attempted_at, now))
            if mode == "manual":
                db.execute("INSERT INTO decisions VALUES(?,?,?,?)",
                           (action.source_run, SHA, "approved", WHEN.isoformat()))

    def claim(self, action=None, obs=None, *, paused=False,
              preflight_verified=True, friend_status="clear", at=WHEN):
        return self.lab.simulated_claim(
            action or self.manual, obs or self.manual_obs, at=at,
            paused=paused, preflight_verified=preflight_verified,
            friend_status=friend_status)

    def test_synthetic_manual_head_passes_shared_legacy_policy_without_network(self):
        self.job(self.manual)
        result = self.claim()
        self.assertEqual((result.state,result.reason),
                         ("intent_simulated","legacy_checks_passed"))
        self.assertTrue(result.simulated)
        self.assertFalse(result.acted)
        with sqlite3.connect(self.file) as db:
            row = db.execute("SELECT state,attempted_at FROM publish_jobs").fetchone()
            self.assertEqual(row[0], "sending_simulated")
            self.assertIsNotNone(row[1])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM r3_lab_audit").fetchone()[0],1)
        self.assertEqual(self.claim().reason, "no_queued_job")

    def test_manual_first_fifo_even_when_auto_was_queued_earlier(self):
        self.job(self.auto, mode="auto", created="2026-10-30T23:10:00+00:00")
        self.job(self.manual, created="2026-10-30T23:20:00+00:00")
        self.assertEqual(self.claim(self.auto,self.auto_obs).reason,
                         "manual_first_queue_head")
        self.assertEqual(self.claim().state, "intent_simulated")
        # An automatic job now encounters real 10-minute spacing.
        later = self.claim(self.auto,self.auto_obs,at=WHEN+timedelta(minutes=11))
        self.assertEqual(later.state, "intent_simulated")

    def test_manual_without_matching_approval_refused(self):
        self.job(self.manual)
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE decisions SET status='rejected'")
        self.assertEqual(self.claim().reason,"manual_approval_missing_or_changed")
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE decisions SET status='approved',draft_sha256=?", ("z"*64,))
        self.assertEqual(self.claim().reason,"manual_approval_missing_or_changed")
        with sqlite3.connect(self.file) as db:
            self.assertIsNone(db.execute(
                "SELECT attempted_at FROM publish_jobs").fetchone()[0])

    def test_auto_disabled_owner_decision_and_friend_gate(self):
        self.job(self.auto,mode="auto")
        self.assertEqual(self.claim(self.auto,self.auto_obs,friend_status="unknown").reason,
                         "friend_review_unproven")
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE publish_settings SET value='0' WHERE name='auto_enabled'")
        self.assertEqual(self.claim(self.auto,self.auto_obs).reason,"auto_disabled")
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE publish_settings SET value='1' WHERE name='auto_enabled'")
            db.execute("INSERT INTO decisions VALUES(?,?,?,?)",
                       (RUN_AUTO,SHA,"approved",WHEN.isoformat()))
        self.assertEqual(self.claim(self.auto,self.auto_obs).reason,
                         "owner_decision_overrides_auto")

    def test_model_text_cannot_replace_the_approved_legacy_scout_draft(self):
        self.job(self.manual)
        changed = replace(self.manual,text="A different reply selected by shadow Bob.")
        self.assertEqual(self.claim(changed,self.manual_obs).reason,
                         "draft_or_source_changed")
        changed_obs=replace(self.manual_obs,approval_sha256="c"*64)
        self.assertEqual(self.claim(obs=changed_obs).reason,"draft_or_source_changed")
        with sqlite3.connect(self.file) as db:
            self.assertIsNone(db.execute(
                "SELECT attempted_at FROM publish_jobs").fetchone()[0])

    def test_pause_or_unverified_preflight_denies_and_does_not_consume_attempt(self):
        self.job(self.manual)
        self.assertEqual(self.claim(paused=True).reason,"global_pause")
        self.assertEqual(self.claim(preflight_verified=False).reason,
                         "preflight_unverified")
        self.assertEqual(self.claim().state,"intent_simulated")

    def test_real_legacy_daily_total_and_auto_limits_cannot_be_overspent(self):
        self.job(self.auto,mode="auto")
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE publish_settings SET value='0' "
                       "WHERE name='activity_limit_comment_auto_daily'")
        self.assertEqual(self.claim(self.auto,self.auto_obs).reason,
                         "legacy_budget_or_spacing")
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE publish_settings SET value='1' "
                       "WHERE name='activity_limit_comment_auto_daily'")
            db.execute("UPDATE publish_settings SET value='2' "
                       "WHERE name='activity_limit_comment_daily'")
            db.execute("INSERT INTO publish_jobs "
                       "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,attempted_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("20261030T190000Z",SHA,
                        "11111111-1111-4111-8111-111111111111","a prior send","manual",
                        "uncertain",WHEN.isoformat(),
                        "2026-10-30T23:25:00+00:00",WHEN.isoformat()))
        self.assertEqual(self.claim(self.auto,self.auto_obs).reason,
                         "legacy_budget_or_spacing")
        # A second historic attempt exhausts total cap even if spacing expires.
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE publish_jobs SET attempted_at='2026-10-30T18:00:00+00:00'"
                       " WHERE state='uncertain'")
            db.execute("INSERT INTO publish_jobs "
                       "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,attempted_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("20261030T180000Z",SHA,
                        "22222222-2222-4222-8222-222222222222","prior send 2","manual",
                        "uncertain",WHEN.isoformat(),
                        "2026-10-30T19:00:00+00:00",WHEN.isoformat()))
        self.assertEqual(self.claim(self.auto,self.auto_obs).reason,
                         "legacy_budget_or_spacing")

    def test_bad_settings_malformed_history_and_unauthorized_target_refused(self):
        self.job(self.manual)
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE publish_settings SET value='999' "
                       "WHERE name='activity_limit_comment_daily'")
        self.assertEqual(self.claim().reason,"invalid_legacy_budget")
        with sqlite3.connect(self.file) as db:
            db.execute("UPDATE publish_settings SET value='2' "
                       "WHERE name='activity_limit_comment_daily'")
            db.execute("INSERT INTO publish_jobs "
                       "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,attempted_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("20261030T190000Z",SHA,
                        "11111111-1111-4111-8111-111111111111","prior send","auto",
                        "uncertain",WHEN.isoformat(),"bad timestamp",WHEN.isoformat()))
        self.assertEqual(self.claim().reason,"legacy_budget_or_spacing")

    def test_existing_attempt_or_uncertain_same_target_locks_new_run(self):
        self.job(self.auto,mode="auto")
        with sqlite3.connect(self.file) as db:
            db.execute("INSERT INTO publish_jobs "
                       "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
                       "created_at,attempted_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("20261030T190000Z",SHA,PID_AUTO,"prior comment","auto",
                        "failed",WHEN.isoformat(),
                        "2026-10-30T20:00:00+00:00",WHEN.isoformat()))
        self.assertEqual(self.claim(self.auto,self.auto_obs).reason,
                         "duplicate_or_uncertain_target")

    def test_synthetic_crash_marks_uncertain_and_cannot_retry(self):
        self.job(self.manual)
        self.assertEqual(self.claim().state,"intent_simulated")
        self.assertEqual(self.lab.simulated_uncertain(RUN_MANUAL, at=WHEN).state,
                         "uncertain_simulated")
        self.assertEqual(self.lab.simulated_uncertain(RUN_MANUAL, at=WHEN).state,
                         "refused")
        with sqlite3.connect(self.file) as db:
            row=db.execute("SELECT state,attempted_at FROM publish_jobs").fetchone()
            self.assertEqual(row[0],"uncertain")
            self.assertIsNotNone(row[1])

    def test_racing_claims_only_one_attempt_and_audit_transaction(self):
        self.job(self.manual)
        def race(_):
            return self.claim()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(race, range(2)))
        self.assertEqual([x.state for x in outcomes].count("intent_simulated"),1)
        with sqlite3.connect(self.file) as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM r3_lab_audit").fetchone()[0],1)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM publish_jobs WHERE attempted_at IS NOT NULL").fetchone()[0],1)

    def test_induced_audit_failure_rolls_back_attempt_intent(self):
        self.job(self.manual)
        with sqlite3.connect(self.file) as db:
            db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON r3_lab_audit "
                       "BEGIN SELECT RAISE(ABORT, 'fixture simulated crash'); END")
        with self.assertRaisesRegex(sqlite3.DatabaseError,"fixture simulated crash"):
            self.claim()
        with sqlite3.connect(self.file) as db:
            self.assertEqual(db.execute(
                "SELECT state,attempted_at FROM publish_jobs").fetchone(),("queued",None))
        with sqlite3.connect(self.file) as db:
            db.execute("DROP TRIGGER fail_audit")
        self.assertEqual(self.claim().state,"intent_simulated")

    def test_rejects_live_legacy_path_and_invalid_private_fixture(self):
        with self.assertRaisesRegex(ValueError,"not_a_compat_lab_path"):
            LegacyCompatLab(self.folder/"activity-queue.sqlite3")._open()
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/"r3-compat-fixtures"/"r3-legacy-compat-lab.sqlite3"
            p.parent.mkdir(mode=0o700)
            with sqlite3.connect(p) as db:
                db.execute("CREATE TABLE r3_lab_meta (name TEXT,value TEXT)")
                db.execute("INSERT INTO r3_lab_meta VALUES('contract','wrong')")
            os.chmod(p,0o600)
            with self.assertRaisesRegex(ValueError,"incorrect_compat_lab_marker"):
                LegacyCompatLab(p)._open()
        symlink=self.folder.parent/"r3-compat-fixtures-other"
        symlink.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "not_a_compat_lab_path"):
            LegacyCompatLab(symlink/self.file.name)._open()

    def test_no_new_network_dispatch_approval_or_external_writes(self):
        import inspect
        import bob_v08.r3_legacy_compat as module
        source=inspect.getsource(module)
        for forbidden in ("urllib", "requests.", "api_key(", "subprocess.run(",
                          "bob_publish_common.connect(", "moltbook.com", "os.system("):
            self.assertNotIn(forbidden, source)
        self.assertFalse(self.lab.simulated_claim(
            self.manual,self.manual_obs,at=WHEN).acted)
        self.assertFalse(self.lab.simulated_claim(
            self.manual,self.manual_obs,at=WHEN).simulated is False)


if __name__ == "__main__":
    unittest.main()
