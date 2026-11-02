"""R4 patch refusal classifier: synthetic read-only probes, no host changes."""
from __future__ import annotations

from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_r4_patch_refusal as diag


class ReadOnlyPatchRefusalTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory(prefix="r4-refusal-readonly-")
        self.addCleanup(folder.cleanup)
        self.home=Path(folder.name)

    def all_ok(self, *, publisher=True, journal_phase="complete"):
        with ExitStack() as stack:
            stack.enter_context(patch.object(diag.u,"STATE_DIR",self.home))
            stack.enter_context(patch.object(diag.u,"registry",return_value={
                "release":diag.OLD}))
            stack.enter_context(patch.object(diag.u,"manifest",return_value={
                "release":diag.NEW,"from":diag.OLD,"restart_manager":True,
                "files":[{"name":name} for name in (
                    "bob-release-updater","bobctl","bob_r4_agent.py",
                    "bob_r4_installed_gate.py")]}))
            stack.enter_context(patch.object(diag.u,"read_journal",return_value={
                "release":diag.OLD,"phase":journal_phase}))
            stack.enter_context(patch.object(diag.u,"live_ok",return_value=True))
            stack.enter_context(patch.object(diag.u,"r4_publisher_inactive",
                                              return_value=publisher))
            stack.enter_context(patch.object(diag.u,"authorization",
                                              return_value="Basic synthetic"))
            stack.enter_context(patch.object(diag.u,"healthy",return_value=True))
            stack.enter_context(patch.object(diag,"_private_directory",return_value=True))
            stack.enter_context(patch.object(diag,"_lock_metadata",return_value=True))
            stack.enter_context(patch.object(diag,"_sqlite_ro",return_value=True))
            return diag.inspect()

    def test_clear_snapshot_remains_no_authority(self):
        report=self.all_ok()
        self.assertEqual(report["current_blockers"],[])
        self.assertTrue(report["currently_no_observed_prearchive_blocker"])
        self.assertEqual(len(report["checks"]),10)
        self.assertFalse(report["historical_failure_reason_known"])
        self.assertFalse(report["retry_authorized_by_report"])
        self.assertFalse(report["patch_installed_by_report"])
        self.assertFalse(report["host_files_changed_by_report"])
        self.assertFalse(report["database_changed_by_report"])
        self.assertFalse(report["services_changed_by_report"])
        self.assertEqual(report["public_social_requests_by_report"],0)

    def test_changed_publisher_or_incomplete_journal_stays_blocked(self):
        inactive=self.all_ok(publisher=False)
        self.assertEqual(inactive["current_blockers"],[
            "publisher_idle_at_snapshot"])
        self.assertFalse(inactive["currently_no_observed_prearchive_blocker"])
        interrupted=self.all_ok(journal_phase="installed")
        self.assertEqual(interrupted["current_blockers"],[
            "completed_prior_journal"])
        self.assertFalse(interrupted["retry_authorized_by_report"])
        self.assertFalse(diag._probe(lambda:(_ for _ in ()).throw(
            ValueError("private content never displayed"))))

    def test_read_only_cli_rejects_install_arguments(self):
        self.assertEqual(diag.main(["--install"]),2)
        c=(ROOT/"scripts/report_r4_patch_refusal.py").read_text()
        for forbidden in (
            "u.update(", "updater.update(", "create_verified_backup(",
            "os.open(", "systemctl", "subprocess.run(", "set_pause(",
            "set_mode(", "requests.post(", "api_key(",
        ):
            self.assertNotIn(forbidden,c)

    def test_archive_presence_and_symlink_would_be_detected(self):
        tx=self.home/("tx-"+diag.NEW)
        self.assertFalse(tx.exists())
        tx.mkdir()
        self.assertTrue(tx.exists())
        tx.rmdir()
        tx.symlink_to(self.home)
        self.assertTrue(tx.is_symlink())


if __name__=="__main__":
    unittest.main()
