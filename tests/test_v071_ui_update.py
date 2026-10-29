"""Isolated v0.7.1 release package and code-only rollback acceptance."""
from pathlib import Path
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_v071_manager_candidate as builder
import rehearse_v071_ui_update as upgrade


def package():
    candidate, nav = builder.build()
    return builder.review_zip(candidate, nav)


def modify_archive(raw, edit):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files = {name: z.read(name) for name in z.namelist()}
    edit(files)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return out.getvalue()


class UIReleaseRehearsalTests(unittest.TestCase):
    def test_verified_package_and_code_only_rollback(self):
        manager, nav = upgrade.inspect_package(package())
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            root = Path(tmp)
            result = upgrade.rehearsal(root, builder.SOURCE.read_bytes(), manager, nav)
            self.assertEqual(result["candidate_files"], 2)
            self.assertTrue(result["atomic_switch_verified"])
            self.assertTrue(result["failed_health_rollback_verified"])
            self.assertTrue(result["post_update_writes_preserved"])
            self.assertFalse(result["live_install_modified"])
            self.assertEqual(upgrade.active(root), "baseline")

    def test_extra_zip_member_refused(self):
        unsafe = modify_archive(package(), lambda files: files.update({"live-credentials": b"test"}))
        with self.assertRaisesRegex(ValueError, "membership"):
            upgrade.inspect_package(unsafe)

    def test_tampered_manager_refused(self):
        def edit(files):
            files["bin/bob-activity-manager"] += b"\n# fake change"
        with self.assertRaisesRegex(ValueError, "checksum"):
            upgrade.inspect_package(modify_archive(package(), edit))

    def test_tampered_navigation_refused(self):
        def edit(files):
            files["bin/navigation_shell.py"] += b"\n# changed"
        with self.assertRaisesRegex(ValueError, "checksum"):
            upgrade.inspect_package(modify_archive(package(), edit))

    def test_manifest_deployable_flag_cannot_be_changed(self):
        def edit(files):
            meta = json.loads(files["REVIEW-MANIFEST.json"])
            meta["deployable"] = True
            files["REVIEW-MANIFEST.json"] = json.dumps(meta).encode()
        with self.assertRaisesRegex(ValueError, "manifest"):
            upgrade.inspect_package(modify_archive(package(), edit))

    def test_refuse_nonempty_staging_root(self):
        manager, nav = upgrade.inspect_package(package())
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            root = Path(tmp)
            (root / "existing.txt").write_text("retain")
            with self.assertRaisesRegex(ValueError, "nonempty"):
                upgrade.make_stage(root, builder.SOURCE.read_bytes(), manager, nav)
            self.assertEqual((root / "existing.txt").read_text(), "retain")

    def test_changed_candidate_is_not_switched(self):
        manager, nav = upgrade.inspect_package(package())
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            root = Path(tmp)
            upgrade.make_stage(root, builder.SOURCE.read_bytes(), manager, nav)
            upgrade.switch(root, "baseline")
            path = root / "releases/candidate/bin/navigation_shell.py"
            path.write_bytes(path.read_bytes() + b"\n# tamper")
            with self.assertRaisesRegex(ValueError, "Tampered"):
                upgrade.switch(root, "candidate")
            self.assertEqual(upgrade.active(root), "baseline")

    def test_unexpected_active_symlink_is_never_replaced(self):
        manager, nav = upgrade.inspect_package(package())
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-") as tmp:
            root = Path(tmp)
            upgrade.make_stage(root, builder.SOURCE.read_bytes(), manager, nav)
            (root / "current").symlink_to("/etc/systemd/system")
            with self.assertRaisesRegex(ValueError, "Unexpected active"):
                upgrade.switch(root, "candidate")
            self.assertEqual(os.readlink(root / "current"), "/etc/systemd/system")


if __name__ == "__main__":
    unittest.main()
