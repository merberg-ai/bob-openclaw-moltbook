"""CH-HTTPS1 strict transport/rollback contracts, synthetic and offline.

Never opens a real network socket, installed credential, service or SQLite DB.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import ssl
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as upd


def load_bobctl():
    file=ROOT/"src/bin/bobctl"
    spec=importlib.util.spec_from_file_location("ch_https1_bobctl",file)
    if spec is None:
        # Extensionless scripts require SourceFileLoader.
        from importlib.machinery import SourceFileLoader
        loader=SourceFileLoader("ch_https1_bobctl",str(file))
        spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec)
    with patch.dict(os.environ,dict(os.environ)):
        spec.loader.exec_module(module)
    return module


class UpdaterTransportTests(unittest.TestCase):
    def test_release_modes_are_explicit_and_do_not_guess(self):
        self.assertEqual(upd.manager_transport("v0.8.0-r3stage1"),"http")
        self.assertEqual(upd.manager_transport("v0.8.0-chhttps1"),"http")
        self.assertEqual(upd.manager_transport("v0.8.0-chhttps3"),"https")
        for x in ("other", "v0.8.0-chhttps2",None,123):
            if x is None:
                with patch.object(upd,"registry",return_value={"release":"other"}):
                    with self.assertRaises(ValueError):
                        upd.manager_transport(x)
            else:
                with self.assertRaises(ValueError):
                    upd.manager_transport(x)

    def test_https_ca_is_private_and_tls_12_and_host_validation_stay_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"manager-tls"
            root.mkdir(mode=0o700)
            ca=root/"ca.crt"
            ca.write_text("synthetic certificate bytes")
            ca.chmod(0o600)
            with patch.object(upd,"TLS_DIR",root), patch.object(upd,"TLS_CA",ca):
                mock_ctx=MagicMock()
                mock_ctx.check_hostname=True
                mock_ctx.verify_mode=ssl.CERT_REQUIRED
                with patch.object(upd.ssl,"create_default_context",return_value=mock_ctx) as build:
                    self.assertIs(upd.manager_tls_context(),mock_ctx)
                    self.assertEqual(mock_ctx.minimum_version,ssl.TLSVersion.TLSv1_2)
                    build.assert_called_once_with(cafile=str(ca))
                ca.chmod(0o644)
                with patch.object(upd.ssl,"create_default_context") as build:
                    with self.assertRaises(ValueError):
                        upd.manager_tls_context()
                    build.assert_not_called()
                ca.chmod(0o600)
                ca.unlink()
                ca.symlink_to(root/"does-not-exist")
                with patch.object(upd.ssl,"create_default_context") as build:
                    with self.assertRaises(ValueError):
                        upd.manager_tls_context()
                    build.assert_not_called()

    def test_https_connection_must_use_fixed_port_host_ca_no_plaintext_fallback(self):
        context=MagicMock()
        with patch.object(upd,"manager_tls_context",return_value=context), \
             patch.object(upd,"HTTPSConnection") as https, \
             patch.object(upd,"HTTPConnection") as http:
            upd._manager_connection(release="v0.8.0-chhttps3",timeout=6)
            https.assert_called_once_with("127.0.0.1",18790,timeout=6,context=context)
            http.assert_not_called()
        with patch.object(upd,"manager_tls_context",side_effect=ValueError("bad CA")), \
             patch.object(upd,"HTTPSConnection") as https, \
             patch.object(upd,"HTTPConnection") as http:
            self.assertFalse(upd.healthy("Basic synthetic",release="v0.8.0-chhttps3"))
            https.assert_not_called()
            http.assert_not_called()

    def test_http_exact_legacy_routes_no_other_host(self):
        response=MagicMock()
        response.status=200
        response.read.side_effect=[
            b'{"ok":true}',
            b"<html>settings</html>",
            b"<html>activity</html>",
            b"<html>system status</html>",
            b'{"services":[]}',
        ]
        conn=MagicMock()
        conn.getresponse.return_value=response
        with patch.object(upd,"HTTPConnection",return_value=conn) as http,\
             patch.object(upd,"HTTPSConnection") as https:
            self.assertTrue(upd.healthy("Basic synthetic",release="v0.8.0-chhttps1"))
            self.assertEqual(conn.request.call_count,5)
            self.assertEqual(conn.close.call_count,5)
            http.assert_called_with("127.0.0.1",18790,timeout=16)
            https.assert_not_called()
        for args,kwargs in conn.request.call_args_list:
            self.assertEqual(args[0],"GET")
            self.assertEqual(kwargs["headers"]["Host"],"127.0.0.1:18790")

    def test_https_invalid_handshake_never_uses_http(self):
        with patch.object(upd,"manager_tls_context",return_value=MagicMock()), \
             patch.object(upd,"HTTPSConnection") as https,\
             patch.object(upd,"HTTPConnection") as http:
            https.return_value.request.side_effect=ssl.SSLCertVerificationError(
                "synthetic hostname mismatch")
            self.assertFalse(upd.healthy("Basic synthetic",release="v0.8.0-chhttps3"))
            http.assert_not_called()

    def test_pre_candidate_and_rollback_health_probe_release_is_explicit(self):
        source=(ROOT/"scripts/bob_release_updater.py").read_text()
        self.assertIn('healthy(auth,release=current["release"])',source)
        self.assertIn('wait_for_health(auth,release=plan["release"])',source)
        self.assertIn('wait_for_health(auth,release=old_registry["release"])',source)
        self.assertNotIn("verify=False",source)
        self.assertNotIn("check_hostname=False",source)
        with patch.object(upd,"healthy",return_value=True) as probe:
            self.assertTrue(upd.wait_for_health(
                "Basic synthetic",seconds=1,release="v0.8.0-chhttps3"))
            probe.assert_called_once_with("Basic synthetic",
                                          release="v0.8.0-chhttps3")

    def test_diagnostic_only_release_keeps_strict_https_without_manager_restart(self):
        import json
        plan=json.loads((ROOT/"releases/candidates/r3-canary1-exact-manual.json").read_text())
        self.assertEqual(upd.manifest(ROOT)["release"],"v0.8.0-r4propose1")
        self.assertEqual(plan["release"],"v0.8.0-r3canary1")
        self.assertEqual(plan["from"],"v0.8.0-r3skip1")
        self.assertFalse(plan["restart_manager"])
        self.assertEqual(upd.manager_transport(plan["release"]),"https")
        self.assertEqual({i["name"] for i in plan["files"]},
                         {"bob-release-updater","bobctl","bob_r3_package.pyz",
                          "bob_r3_canary_lock.py","bob_r313c_adapter.py",
                          "bob-moltbook-publisher","bob-r3-canary-arm"})
        self.assertNotIn("bob-activity-manager",{i["name"] for i in plan["files"]})
        self.assertIn("bob-moltbook-publisher",{i["name"] for i in plan["files"]})
        for item in plan["files"]:
            payload=upd.release_bytes(ROOT,item)
            if not item["name"].endswith(".pyz"):
                compile(payload,item["name"],"exec")


class BobctlTransportTests(unittest.TestCase):
    def test_installed_release_hash_controls_bobctl_mode(self):
        ctl=load_bobctl()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            bins=path/"bin"
            bins.mkdir()
            manager=bins/"bob-activity-manager"
            manager.write_bytes(b"synthetic unchanged installed manager")
            manager.chmod(0o700)
            registry=path/"installed.json"
            def record(release,sha):
                registry.write_text(json.dumps({"format":"bob-updater-v1",
                    "release":release,"files":{"bob-activity-manager":sha}}))
                registry.chmod(0o600)
            valid=hashlib.sha256(manager.read_bytes()).hexdigest()
            with patch.object(ctl,"BIN",bins),patch.object(
                    ctl,"MANAGER_REGISTRY",registry):
                record("v0.8.0-chhttps1",valid)
                self.assertEqual(ctl._manager_transport(),"http")
                record("v0.8.0-chhttps3",valid)
                self.assertEqual(ctl._manager_transport(),"https")
                record("v0.8.0-chhttps3","a"*64)
                with self.assertRaises(ValueError):
                    ctl._manager_transport()
                record("unknown",valid)
                with self.assertRaises(ValueError):
                    ctl._manager_transport()

    def test_bobctl_health_uses_verified_https_not_http_when_selected(self):
        ctl=load_bobctl()
        conn=MagicMock()
        answer=MagicMock(status=200)
        answer.read.return_value=b'{"ok":true,"publishes":false}'
        conn.getresponse.return_value=answer
        with patch.object(ctl,"_manager_transport",return_value="https"),\
             patch.object(ctl,"_manager_connection",return_value=conn) as make:
            self.assertEqual(ctl._manager_health()["publishes"],False)
            make.assert_called_once_with("https")
            conn.request.assert_called_once_with(
                "GET","/healthz",headers={"Host":"127.0.0.1:18790"})
        with patch.object(ctl,"_manager_transport",side_effect=ValueError),\
             patch.object(ctl,"service_state",return_value="active"):
            self.assertFalse(ctl.check_manager()[0])
            self.assertIn("not verified",ctl.check_manager()[1])


if __name__=="__main__":
    unittest.main()
