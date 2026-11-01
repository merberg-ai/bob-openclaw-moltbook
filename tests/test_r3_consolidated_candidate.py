"""R3 integrated candidate packaging tests. Source only; no network or services."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"scripts"), str(ROOT/"src/lib/bob")]
import report_r3_consolidated_candidate as candidate
import bob_release_updater as updater


class R3IntegratedOffCandidateTests(unittest.TestCase):
    def test_package_builds_from_exact_current_https_release_but_cannot_install(self):
        result = candidate.inspect()
        self.assertEqual(result["source_candidate"],"verified")
        self.assertEqual(result["files_built"],12)
        self.assertEqual(len(result["source_hashes"]),12)
        self.assertEqual(result["source_gates"],"four_hard_off")
        self.assertEqual(result["dashboard_transport"],"https_only")
        self.assertFalse(result["ready_to_install_or_cutover"])
        self.assertFalse(result["r3_real_publishing_authorized"])
        self.assertFalse(result["private_db_or_credentials_read"])
        self.assertFalse(result["installed_files_or_systemd_modified"])
        self.assertEqual(result["moltbook_requests"],0)

    def test_verification_and_build_are_stable(self):
        first=candidate.inspect()
        second=candidate.inspect()
        self.assertEqual(first["source_hashes"],second["source_hashes"])
        self.assertEqual(
            updater.manager_transport("v0.8.0-chhttps3"),"https")
        self.assertEqual(
            updater.manager_transport("v0.8.0-cutover1"),"https")
        for unexpected in ("v0.8.0-cutover0","v0.8.0-cutover2"):
            with self.assertRaises(ValueError):
                updater.manager_transport(unexpected)

    def test_candidate_does_not_change_promoted_release(self):
        current=json.loads((ROOT/"releases/current.json").read_text())
        plan=json.loads((ROOT/"releases/candidates/r3-cutover1-integration-off.json").read_text())
        self.assertEqual(current["release"],"v0.8.0-r3diag1")
        self.assertEqual(plan["from"],"v0.8.0-chhttps3")
        self.assertEqual(plan["release"],current["from"])
        self.assertEqual({row["name"] for row in current["files"]},
                         {"bob-release-updater","bobctl","bob_r3_package.pyz"})
        self.assertTrue(candidate.inspect(build=False)["releases_current_json_modified"])
        self.assertTrue(plan["restart_manager"])
        self.assertFalse(current["restart_manager"])
        self.assertIn("bob-moltbook-publisher",{x["name"] for x in plan["files"]})
        self.assertNotIn("bob-moltbook-publisher.timer",{x["name"] for x in plan["files"]})
        self.assertNotIn("bob-r3-publisher",{x["name"] for x in plan["files"]})

    def test_mocked_public_socket_and_credentials_cannot_activate(self):
        import bob_r312_adapter, bob_r313c_adapter
        self.assertFalse(bob_r312_adapter.R312_REAL_DISPATCH)
        self.assertFalse(bob_r313c_adapter.R313C_REAL_DISPATCH)
        self.assertFalse(bob_r313c_adapter.production_dispatch_enabled())
        self.assertFalse(candidate._literal_constant(
            ROOT/"src/lib/bob/bob_r312_adapter.py","R312_REAL_DISPATCH"))
        self.assertTrue(candidate._literal_constant(
            ROOT/"src/bin/bob-moltbook-publisher",
            "R313C_INTEGRATION_COMPILED_OFF"))

    def test_hard_off_prevents_archive_import_or_credentials(self):
        import bob_r313c_adapter as adapter
        with patch.object(adapter, "production_dispatch_enabled",
                          return_value=False), patch.dict(
                          sys.modules, {"bob_r313d_package": None}):
            self.assertIsNone(adapter.maybe_r3_publisher_step(
                None, api_call=lambda *a, **kw: self.fail("no network"),
                credential_loader=lambda: self.fail("no key")))

    def test_future_gate_fails_closed_if_archive_invalid_or_host_untrusted(self):
        import bob_r313c_adapter as adapter
        from types import SimpleNamespace
        calls=[]
        def load():
            calls.append("archive")
            raise ValueError("corrupt registry")
        with patch.object(adapter, "production_dispatch_enabled",return_value=True), \
             patch.dict(sys.modules, {
                 "bob_r313d_package":SimpleNamespace(load_verified=load)}):
            result=adapter.maybe_r3_publisher_step(
                None, api_call=lambda *a, **kw: self.fail("no network"),
                credential_loader=lambda: self.fail("no key"))
        self.assertEqual(result,"R3 candidate fail-closed; no send")
        self.assertEqual(calls,["archive"])
        with patch.object(adapter, "production_dispatch_enabled",return_value=True), \
             patch.dict(sys.modules, {"bob_r313d_package":None}):
            missing=adapter.maybe_r3_publisher_step(
                None, api_call=lambda *a, **kw: self.fail("no network"),
                credential_loader=lambda: self.fail("no key"))
        self.assertEqual(missing,"R3 candidate fail-closed; no send")
        with patch.object(adapter, "production_dispatch_enabled",return_value=True), \
             patch.object(adapter,"_trusted_single_publisher_db",return_value=False), \
             patch.dict(sys.modules,{
                 "bob_r313d_package":SimpleNamespace(
                    load_verified=lambda:"verified_registry_archive")}):
            result=adapter.maybe_r3_publisher_step(
                None, api_call=lambda *a, **kw: self.fail("no network"),
                credential_loader=lambda: self.fail("no key"))
        self.assertEqual(result,"R3 candidate host boundary refused; no send")

    def test_source_gate_drift_prevents_candidate(self):
        with patch.object(candidate,"_literal_constant",return_value=False):
            with self.assertRaisesRegex(ValueError,"gate is not Off"):
                candidate.inspect(build=False)

    def test_extra_target_or_release_chain_drift_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            new_root=Path(temp)
            (new_root/"releases/candidates").mkdir(parents=True)
            (new_root/"src/bin").mkdir(parents=True)
            (new_root/"src/lib/bob").mkdir(parents=True)
            old=json.loads((ROOT/"releases/current.json").read_text())
            plan=json.loads((ROOT/"releases/candidates/r3-cutover1-integration-off.json").read_text())
            (new_root/"releases/current.json").write_text(json.dumps(old))
            def write(p): (new_root/"releases/candidates/r3-cutover1-integration-off.json").write_text(json.dumps(p))
            plan["files"].append({"name":"bob-untrusted-new","source":"src/bin/evil"})
            write(plan)
            with self.assertRaises(ValueError):
                candidate.inspect(root=new_root,build=False)
            plan["files"].pop()
            plan["from"]="v0.8.0-shadow4"
            write(plan)
            with self.assertRaises(ValueError):
                candidate.inspect(root=new_root,build=False)
            plan["from"]="v0.8.0-chhttps3"
            old["release"]="v0.8.0-shadow4"
            (new_root/"releases/current.json").write_text(json.dumps(old))
            write(plan)
            with self.assertRaises(ValueError):
                candidate.inspect(root=new_root,build=False)

    def test_readonly_cli_rejects_extra_flags(self):
        self.assertEqual(candidate.main([]),2)
        self.assertEqual(candidate.main(["--install"]),2)
        with patch.object(candidate,"inspect",return_value={
            "source_candidate":"verified","from":"v0.8.0-chhttps3",
            "release":"v0.8.0-cutover1","files_built":12,
            "source_gates":"four_hard_off",
            "single_existing_credentialed_publisher":True,
            "publisher_atomic_duplicate_guard_present":True,
            "dashboard_transport":"https_only",
            "releases_current_json_modified":True}):
            self.assertEqual(candidate.main(["--check"]),0)


if __name__=="__main__":
    unittest.main()
