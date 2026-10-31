"""CH-HTTPS3 real ephemeral TLS-only manager candidate and HTTPS origin tests.

All keys, Basic credentials, manager, updater registry and queue are synthetic
in a temporary HOME; only loopback ephemeral sockets. No WSL, installed unit,
Moltbook API, Windows trust or real publisher changes.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_ch_https3_manager_candidate as builder
import build_r313d_manager_candidate as prior
import build_r313d_off_package as r3
import build_v08_shadow_package as shadow

CHILD=r"""
from http.client import HTTPConnection,HTTPSConnection
from http.server import ThreadingHTTPServer
import base64
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import pwd
import ssl
import threading
from urllib.parse import urlencode
import sys
# Synthetic fake HOME is guarded from the live account by requiring a
# mocked owner identity only in this ephemeral test process.
home=Path.home()
real_getpwuid=pwd.getpwuid
pwd.getpwuid=lambda uid:type("SyntheticAccount",(),{
    "pw_dir":str(home),"pw_name":"openclaw"})()
loader=SourceFileLoader("ch_https3_synthetic_manager",sys.argv[1])
spec=importlib.util.spec_from_loader(loader.name,loader)
mgr=importlib.util.module_from_spec(spec)
loader.exec_module(mgr)
from bob_manager_tls import tls_context
ctx=tls_context()
srv=ThreadingHTTPServer(("127.0.0.1",0),mgr.Handler)
srv.socket=ctx.wrap_socket(srv.socket,server_side=True)
thread=threading.Thread(target=srv.serve_forever,daemon=True)
thread.start()
auth="Basic "+base64.b64encode(b"chhttps3-test-user:long-synthetic-password-1234").decode()
context=ssl.create_default_context(
    cafile=str(home/".config/bob-system/manager-tls/ca.crt"))
context.minimum_version=ssl.TLSVersion.TLSv1_2
try:
    def request(method,path,*,authenticated=False,origin=None,host="127.0.0.1:18790",
                data=None,fetch=None):
        conn=HTTPSConnection("127.0.0.1",srv.server_port,context=context,timeout=3)
        headers={"Host":host}
        if authenticated:headers["Authorization"]=auth
        if origin is not None:headers["Origin"]=origin
        if fetch is not None:headers["Sec-Fetch-Site"]=fetch
        body=urlencode(data).encode() if data else None
        if body is not None:headers["Content-Type"]="application/x-www-form-urlencoded"
        conn.request(method,path,body=body,headers=headers)
        res=conn.getresponse()
        result=(res.status,res.read(65537),res.getheader("Strict-Transport-Security"))
        conn.close()
        return result
    assert request("GET","/r3")[0]==401
    assert request("GET","/r3",authenticated=True,host="attacker.example")[0]==403
    status,body,hsts=request("GET","/r3",authenticated=True)
    assert status==200
    assert b"Bob R3 Controls" in body
    assert b"R3 automatic publishing" in body
    assert hsts=="max-age=31536000"
    assert request("GET","/activity",authenticated=True)[0]==200
    assert request("GET","/v08/now",authenticated=True)[0]==200
    assert request("GET","/v08/inbox",authenticated=True)[0]==200
    data={"csrf":mgr.TOKEN,"confirmation":"ENABLE R3 MANUAL"}
    # Basic + CSRF cannot bypass strict HTTPS origin validation.
    assert request("POST","/r3/mode/manual-on",authenticated=True,
                   origin="http://127.0.0.1:18790",data=data)[0]==403
    assert request("POST","/r3/mode/manual-on",authenticated=True,
                   origin="https://attacker.example",data=data)[0]==403
    assert request("POST","/r3/mode/manual-on",authenticated=True,
                   origin="https://127.0.0.1:18790",data={"csrf":"wrong",
                      "confirmation":"ENABLE R3 MANUAL"})[0]==403
    # Correct HTTPS origin proceeds to independent source/owner boundary,
    # which is still Off and cannot mutate synthetic fixture.
    assert request("POST","/r3/mode/manual-on",authenticated=True,
                   origin="https://127.0.0.1:18790",data=data)[0]==409
    assert request("POST","/r3/mode/manual-on",authenticated=True,
                   origin="https://127.0.0.1:18790",data=data,
                   fetch="cross-site")[0]==403
    from bob_publish_common import connect
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM publish_jobs").fetchone()==(0,)
        assert db.execute("SELECT value FROM publish_settings "
                          "WHERE name='r3_manual_enabled'").fetchone() is None
    # A raw HTTP request cannot obtain even the Basic-auth challenge,
    # since TLS handshake is mandatory before HTTP handlers run.
    try:
        plain=HTTPConnection("127.0.0.1",srv.server_port,timeout=1.2)
        try:
            plain.request("GET","/healthz")
            res=plain.getresponse()
            raise AssertionError("plaintext accepted HTTP status "+str(res.status))
        finally:
            plain.close()
    except (ConnectionResetError,ConnectionAbortedError,TimeoutError,
            ssl.SSLError,OSError):
        pass
    # Wrong/untrusted CA fails, cannot fall back to HTTP.
    wrong=ssl.create_default_context()
    try:
        conn=HTTPSConnection("127.0.0.1",srv.server_port,context=wrong,timeout=3)
        conn.request("GET","/healthz")
        conn.getresponse()
        raise AssertionError("untrusted CA accepted")
    except ssl.SSLCertVerificationError:
        pass
    finally:
        conn.close()
    print("CH-HTTPS3 TLS-only authentic /r3, old routes, HTTPS Origin/CSRF, plaintext refusal: PASS")
finally:
    srv.shutdown()
    srv.server_close()
    thread.join(timeout=3)
"""


class HTTPS3CandidateTests(unittest.TestCase):
    def test_source_builder_preserves_R3_nav_and_hard_TLS_only(self):
        manager,nav=builder.build()
        old, oldnav=prior.build()
        self.assertEqual(nav,oldnav)
        self.assertIn(b"serve_tls(Handler, HOST, PORT)",manager)
        self.assertIn(b"HTTPSOnlyHandlerMixin",manager)
        self.assertNotIn(
            b"ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()",manager)
        self.assertIn(b"from bob_r313d_web import R3HandlerMixin",manager)
        self.assertGreater(len(manager),len(old))

    def test_generated_manager_real_synthetic_tls_and_browser_protections(self):
        from unittest.mock import patch
        import prepare_ch_https2 as certificates
        with tempfile.TemporaryDirectory(prefix="chhttps3-real-tls-") as tmp:
            root=Path(tmp)
            home=root/"home"
            config=home/".config/bob-system"
            tls=config/"manager-tls"
            tls.mkdir(parents=True,mode=0o700)
            # pathlib creates implicit parent directories with default mode.
            # The real Bob parent is 0700; mirror that trusted fixture.
            config.chmod(0o700)
            with patch.object(certificates,"OPENSSL",Path("/usr/bin/openssl")):
                with patch.object(certificates,"TLS_DIR",tls):
                    certificates._generate(tls)
            (config/"lan-auth.json").write_text(json.dumps({
                "username":"chhttps3-test-user",
                "password":"long-synthetic-password-1234"}))
            (config/"lan-auth.json").chmod(0o600)
            bin_dir=root/"bin"
            bin_dir.mkdir()
            installed=home/".local/bin"
            installed.mkdir(parents=True)
            state=home/".local/state/bob-updater"
            state.mkdir(parents=True)
            z2,_=shadow.build()
            z3,_=r3.build()
            for name,raw in (
                    ("bob_v08_package.pyz",z2),
                    ("bob_r3_package.pyz",z3)):
                p=installed/name
                p.write_bytes(raw)
                p.chmod(0o700)
            registry=state/"installed.json"
            registry.write_text(json.dumps({
                "format":"bob-updater-v1",
                "release":"v0.8.0-chhttps1",
                "files":{
                    "bob_v08_package.pyz":hashlib.sha256(z2).hexdigest(),
                    "bob_r3_package.pyz":hashlib.sha256(z3).hexdigest(),
                }}))
            registry.chmod(0o600)
            manager,nav=builder.build()
            manager_path=bin_dir/"bob-activity-manager"
            manager_path.write_bytes(manager)
            (bin_dir/"navigation_shell.py").write_bytes(nav)
            env={**os.environ,
                 "HOME":str(home),
                 "PYTHONPATH":os.pathsep.join([
                    str(bin_dir),str(ROOT/"src/lib/bob"),str(ROOT/"src")]),
                 "BOB_MANAGER_BIND":"0.0.0.0",
                 "BOB_MANAGER_PORT":"18790",
                 "PYTHONDONTWRITEBYTECODE":"1"}
            outcome=subprocess.run(
                [sys.executable,"-c",CHILD,str(manager_path)],
                cwd=root,env=env,capture_output=True,text=True,timeout=24)
            self.assertEqual(outcome.returncode,0,outcome.stderr[-2800:])
            self.assertIn("TLS-only authentic /r3",outcome.stdout)

    def test_fixed_manifest_is_unpromoted_two_files(self):
        import json
        data=json.loads((ROOT/"releases/candidates/ch-https3-tls-manager.json").read_text())
        self.assertEqual(data["from"],"v0.8.0-chhttps1")
        self.assertEqual(data["release"],"v0.8.0-chhttps3")
        self.assertEqual({x["name"] for x in data["files"]},
                         {"bob_manager_tls.py","bob-activity-manager"})
        self.assertTrue(data["restart_manager"])
        live=json.loads((ROOT/"releases/current.json").read_text())
        self.assertEqual(live["release"],"v0.8.0-chhttps3")
        self.assertEqual({x["name"] for x in live["files"]},
                         {"bob_manager_tls.py","bob-activity-manager"})
        for item in data["files"]:
            if "builder" in item:
                compile(builder.build()[0],item["name"],"exec")
            else:
                compile((ROOT/item["source"]).read_bytes(),item["name"],"exec")

if __name__=="__main__":
    unittest.main()
