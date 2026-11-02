"""R4 pretransaction diagnostic reports ONLY a fixed stage, never secrets.

All test calls are isolated mocks; no host updater, real DB, service, model
or social API can run. The existing rollout/rollback rehearsal is unchanged.
"""
from __future__ import annotations

from contextlib import ExitStack,redirect_stdout
from io import StringIO
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater

PATCH="v0.8.0-r4propose1"
SECRET="DO_NOT_LEAK_PRIVATE_ERROR_DETAIL"


class PrearchiveStageTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r4-prearchive-stages-")
        self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)
        self.plan={"release":PATCH,"restart_manager":True}
        self.current={"release":"v0.8.0-autonomy1","files":{}}

    def exercise(self, *, publisher=True, journal=None, hash_ok=True,
                 https_ok=True, backup_failure=None, lock_failure=None,
                 plan=None):
        output=StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch.object(updater,"STATE_DIR",self.home))
            stack.enter_context(patch.object(updater,"BIN",self.home))
            stack.enter_context(patch.object(updater,"DB",self.home/"db.sqlite3"))
            stack.enter_context(patch.object(updater,"BACKUP_DIR",self.home))
            stack.enter_context(patch.object(updater,"private_dir"))
            if lock_failure:
                lock=stack.enter_context(patch.object(
                    updater,"locked",side_effect=lock_failure))
            else:
                lock=stack.enter_context(patch.object(
                    updater,"locked",side_effect=lambda:os.open(os.devnull,os.O_RDONLY)))
            stack.enter_context(patch.object(
                updater,"r4_publisher_inactive",return_value=publisher))
            stack.enter_context(patch.object(
                updater,"read_journal",return_value=journal or {"phase":"complete"}))
            stack.enter_context(patch.object(
                updater,"live_ok",return_value=hash_ok))
            stack.enter_context(patch.object(
                updater,"healthy",return_value=https_ok))
            backup=stack.enter_context(patch(
                "backup_live_sqlite.create_verified_backup",
                side_effect=backup_failure if backup_failure is not None
                else lambda *_:{"restore_rehearsal":"passed"}))
            write=stack.enter_context(patch.object(updater,"write_target",
                                                  side_effect=AssertionError(
                                                      "must never install")))
            save=stack.enter_context(patch.object(updater,"save_private",
                                                 side_effect=AssertionError(
                                                     "must never archive")))
            with redirect_stdout(output):
                with self.assertRaises((ValueError,OSError)):
                    updater.update(ROOT,self.current,plan or self.plan,
                                   {},auth="Basic synthetic")
        write.assert_not_called()
        save.assert_not_called()
        return output.getvalue(),backup.call_count

    def test_publisher_race_is_labeled_not_bypassed(self):
        log,calls=self.exercise(publisher=False)
        self.assertEqual(log.strip(),
            "BOB R4 PATCH PREFLIGHT: refused at publisher_topology (ValueError)")
        self.assertEqual(calls,0)

    def test_auth_health_refusal_is_specific_and_no_backup(self):
        log,calls=self.exercise(https_ok=False)
        self.assertIn("refused at authenticated_https (ValueError)",log)
        self.assertEqual(calls,0)

    def test_verified_sqlite_backup_failure_is_specific_but_secrets_hidden(self):
        log,calls=self.exercise(
            backup_failure=ValueError(SECRET))
        self.assertIn("refused at verified_sqlite_backup (ValueError)",log)
        self.assertNotIn(SECRET,log)
        self.assertEqual(calls,1)

    def test_incomplete_journal_before_backup_is_not_recovered_or_ignored(self):
        log,calls=self.exercise(journal={"phase":"migrated"})
        self.assertIn("refused at prior_journal (ValueError)",log)
        self.assertEqual(calls,0)

    def test_updater_lock_failure_is_reported_without_bypassing(self):
        log,calls=self.exercise(lock_failure=ValueError(SECRET))
        self.assertIn("refused at updater_lock (ValueError)",log)
        self.assertNotIn(SECRET,log)
        self.assertEqual(calls,0)

    def test_other_release_does_not_receive_proposal_patch_diagnostics(self):
        log,calls=self.exercise(
            https_ok=False,plan={"release":"v0.8.0-autonomy1",
                                 "restart_manager":True})
        self.assertEqual(log,"")
        self.assertEqual(calls,0)

    def test_label_function_rejects_dynamic_or_unreviewed_stage(self):
        output=StringIO()
        with redirect_stdout(output):
            updater._r4_patch_refusal_stage(
                {"release":PATCH},SECRET,ValueError(SECRET))
            updater._r4_patch_refusal_stage(
                {"release":"v0.8.0-autonomy1"},"publisher_topology",
                ValueError(SECRET))
        self.assertEqual(output.getvalue(),"")


if __name__=="__main__":
    unittest.main()
