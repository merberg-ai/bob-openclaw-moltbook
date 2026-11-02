"""The release lineage is the single source of release identities."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
from unittest.mock import patch
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/lib/bob"))
sys.path.insert(0, str(ROOT / "scripts"))

import bob_release_lineage as lineage  # noqa: E402
import bob_release_updater as updater  # noqa: E402
import bob_r4_installed_gate as gate  # noqa: E402
import bob_r4_schedule as schedule  # noqa: E402

FUTURE = "v0.8.9-lineage-test"

LEGACY_R4 = {"v0.8.0-autonomy1", "v0.8.0-r4propose1", "v0.8.0-r4format1",
             "v0.8.0-r4schedule1", "v0.8.0-r4schedule2"}


class LineageTests(unittest.TestCase):
    def test_unknown_ids_fail_closed(self):
        for bad in (None, "", "v0.8.0-made-up", 7, ["v0.8.0-r4schedule2"], "V0.8.0-R4SCHEDULE2"):
            self.assertFalse(lineage.known(bad))
            self.assertIsNone(lineage.transport(bad))
            self.assertIsNone(lineage.predecessor(bad))
            for fam in lineage.FAMILIES:
                self.assertFalse(lineage.in_family(bad, fam))
        with self.assertRaises(ValueError):
            lineage.in_family("v0.8.0-r4schedule2", "publish")
        with self.assertRaises(ValueError):
            lineage.family("auto")

    def test_behaviour_preserving_for_existing_releases(self):
        self.assertEqual(lineage.family("r4"), LEGACY_R4)
        self.assertEqual(lineage.family("r4_patch"), LEGACY_R4 - {"v0.8.0-autonomy1"})
        self.assertEqual(lineage.family("r4_schedule"), {"v0.8.0-r4schedule1", "v0.8.0-r4schedule2"})
        self.assertEqual(lineage.rollback_predecessors(), {
            "v0.8.0-autonomy1": "v0.8.0-r3canary1",
            "v0.8.0-r4propose1": "v0.8.0-autonomy1",
            "v0.8.0-r4format1": "v0.8.0-r4propose1",
            "v0.8.0-r4schedule1": "v0.8.0-r4format1",
            "v0.8.0-r4schedule2": "v0.8.0-r4schedule1",
        })
        self.assertEqual(lineage.transport("v0.8.0-r3stage1"), "http")
        self.assertEqual(lineage.transport("v0.8.0-chhttps1"), "http")
        self.assertEqual(gate.SUPPORTED, LEGACY_R4)

    def test_updater_and_bobctl_use_identical_transport_table(self):
        self.assertEqual(updater.MANAGER_TRANSPORTS, lineage.manager_transports())
        tree = ast.parse((ROOT / "src/bin/bobctl").read_text())
        table = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign)
                     and any(getattr(t, "id", "") == "MANAGER_TRANSPORTS" for t in node.targets))
        self.assertEqual(table, lineage.manager_transports(),
                         "bobctl is self-contained by design; keep its table identical to the lineage")

    def test_current_manifest_release_is_in_lineage(self):
        manifest = json.loads((ROOT / "releases/current.json").read_text())
        self.assertTrue(lineage.known(manifest["release"]))
        self.assertTrue(lineage.known(manifest["from"]) or manifest["from"] not in lineage.RELEASES)
        self.assertEqual(lineage.LATEST, manifest["release"],
                         "bump LATEST together with releases/current.json")
        if manifest["release"] not in gate.PRE_LINEAGE:
            names = {f["name"] for f in manifest["files"]}
            self.assertIn("bob_release_lineage.py", names,
                          "post-lineage releases must ship the lineage module")

    def test_no_component_reintroduces_r4_release_lists(self):
        """Literal multi-release tuples of R4 ids belong in the lineage only."""
        for rel in ("scripts/bob_release_updater.py", "src/lib/bob/bob_r4_installed_gate.py",
                    "src/lib/bob/bob_r4_schedule.py", "scripts/report_r4_installed.py"):
            tree = ast.parse((ROOT / rel).read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Tuple, ast.Set, ast.List)):
                    ids = [e.value for e in node.elts if isinstance(e, ast.Constant)
                           and isinstance(e.value, str) and e.value.startswith("v0.8.0-r4")]
                    self.assertLess(len(ids), 2, f"{rel}:{node.lineno} lists R4 releases {ids}")


class ScheduleJournalAcrossReleases(unittest.TestCase):
    """A later signed release must not force R4 recover/restage/enable,
    but the exact unit bytes are still enforced."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.journal = Path(self.tmp.name) / "journal.json"
        releases = dict(lineage.RELEASES)
        releases[FUTURE] = ("v0.8.0-r4schedule2", "https",
                            frozenset({"r4", "r4_patch", "r4_schedule"}))
        for p in (patch.object(lineage, "RELEASES", releases),
                  patch.object(lineage, "LATEST", FUTURE),
                  patch.object(schedule, "RELEASE", FUTURE),
                  patch.object(schedule, "JOURNAL", self.journal),
                  patch.object(schedule, "_file", lambda *_a, **_k: True)):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, release, units=None):
        units = units or {n: hashlib.sha256(b.encode()).hexdigest()
                          for n, b in schedule.UNIT_TEXT.items()}
        self.journal.write_text(json.dumps({
            "format": schedule.FORMAT, "release": release, "phase": "enabled",
            "units": units, "public_send_authorized": False}))
        os.chmod(self.journal, 0o600)

    def test_schedule2_journal_accepted_after_newer_release(self):
        self.write("v0.8.0-r4schedule2")
        self.assertEqual(schedule._phase(), "enabled")

    def test_unknown_or_non_schedule_release_journal_refused(self):
        for rel in ("v0.8.0-r4format1", "v0.8.0-made-up", None):
            self.write(rel)
            with self.assertRaises(ValueError):
                schedule._phase()

    def test_changed_unit_bytes_still_refused(self):
        self.write("v0.8.0-r4schedule2", units={n: "0" * 64 for n in schedule.UNIT_TEXT})
        with self.assertRaises(ValueError):
            schedule._phase()

    def test_public_send_flag_still_refused(self):
        self.write("v0.8.0-r4schedule2")
        data = json.loads(self.journal.read_text())
        data["public_send_authorized"] = True
        self.journal.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            schedule._phase()


if __name__ == "__main__":
    unittest.main()
