"""R3.13d actual loopback HTTP smoke with LAN Basic auth and CSRF.

Offline, synthetic HOME only: generated manager from accepted R2/FM4.1/OC4
chain plus isolated R3 mixin. No real credentials, API, publisher or network.
Server listens on ephemeral 127.0.0.1 only, even though synthetic manager's
configured bind value activates LAN Basic auth.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_r313d_manager_candidate as builder
import build_r313d_off_package as r3_builder
import build_v08_shadow_package as r2_builder

CHILD=r"""
import base64
import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader,module_from_spec
import threading
import sys
import os
from urllib.parse import urlencode
os.umask(0o077)
loader=SourceFileLoader("bob_r313d_http_smoke",sys.argv[1])
spec=spec_from_loader(loader.name,loader)
mod=module_from_spec(spec)
loader.exec_module(mod)
assert mod.LAN_CREDS is not None, "synthetic LAN auth not active"
auth="Basic "+base64.b64encode(b"r3-fixture-user:synthetic-long-password-9999").decode()
server=ThreadingHTTPServer(("127.0.0.1",0),mod.Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
try:
    def req(method,path,*,authn=False,host="127.0.0.1:18790",
            origin=None,body=None):
        con=HTTPConnection("127.0.0.1",server.server_port,timeout=3)
        data=urlencode(body).encode() if body else None
        con.putrequest(method,path,skip_host=True)
        con.putheader("Host",host)
        if authn:
            con.putheader("Authorization",auth)
        if origin is not None:
            con.putheader("Origin",origin)
        if data is not None:
            con.putheader("Content-Type","application/x-www-form-urlencoded")
            con.putheader("Content-Length",str(len(data)))
        con.endheaders(data)
        res=con.getresponse()
        code=res.status
        page=res.read().decode("utf-8")
        con.close()
        return code,page
    assert req("GET","/r3")[0]==401, "R3 GET cannot bypass LAN Basic auth"
    assert req("GET","/r3",authn=True,host="attacker.example")[0]==403
    status,page=req("GET","/r3",authn=True)
    assert status==200,(status,page[:300])
    assert "Bob R3 Controls" in page
    assert "The R3 schema is absent or host verification failed" in page,page[:700]
    import bob_v08
    assert str(os.path.expanduser("~/.local/bin/bob_r3_package.pyz"))+"/bob_v08" in bob_v08.__path__,bob_v08.__path__
    from bob_v08.r313c_candidate import ENVELOPE_DDL
    assert "r313c_action_envelopes" in ENVELOPE_DDL
    assert req("GET","/activity",authn=True)[0]==200
    assert req("GET","/v08/now",authn=True)[0]==200
    assert req("GET","/v08/inbox",authn=True)[0]==200
    assert req("POST","/r3/mode/manual-on",authn=False,
               origin="http://127.0.0.1:18790",
               body={"csrf":"random","confirmation":"ENABLE R3 MANUAL"})[0]==401
    assert req("POST","/r3/mode/manual-on",authn=True,
               origin="http://attacker.example",
               body={"csrf":"random","confirmation":"ENABLE R3 MANUAL"})[0]==403
    assert req("POST","/r3/mode/manual-on",authn=True,
               origin="http://127.0.0.1:18790",
               body={"csrf":"random","confirmation":"ENABLE R3 MANUAL"})[0]==403
    assert req("POST","/r3/mode/manual-on",authn=True,
               origin="http://127.0.0.1:18790",
               body={"csrf":mod.TOKEN,
                     "confirmation":"ENABLE R3 MANUAL"})[0]==409
    from bob_publish_common import connect
    with connect() as db:
        assert db.execute("SELECT name FROM publish_settings "
                          "WHERE name='r3_manual_enabled'").fetchone() is None
        assert db.execute("SELECT COUNT(*) FROM publish_jobs").fetchone()[0]==0
    print("R3.13d LAN HTTP + exact Host/Origin/CSRF + old routes: PASS")
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
"""


class R313DRealHttpTests(unittest.TestCase):
    def test_generated_manager_ephemeral_authenticated_http(self):
        manager,nav=builder.build()
        with tempfile.TemporaryDirectory(prefix="bob-r313d-http-") as tmp:
            root=Path(tmp)
            bin_dir=root/"bin"
            home=root/"home"
            auth_dir=home/".config/bob-system"
            bin_dir.mkdir()
            auth_dir.mkdir(parents=True,mode=0o700)
            installed=home/".local/bin"
            installed.mkdir(parents=True,mode=0o700)
            state=home/".local/state/bob-updater"
            state.mkdir(parents=True,mode=0o700)
            r2zip,_=r2_builder.build()
            r3zip,_=r3_builder.build()
            for name,raw in (
                    ("bob_v08_package.pyz",r2zip),
                    ("bob_r3_package.pyz",r3zip)):
                target=installed/name
                target.write_bytes(raw)
                target.chmod(0o700)
            registry=state/"installed.json"
            registry.write_text(json.dumps({
                "format":"bob-updater-v1",
                "release":"v0.8.0-r3stage1",
                "files":{
                    "bob_v08_package.pyz":hashlib.sha256(r2zip).hexdigest(),
                    "bob_r3_package.pyz":hashlib.sha256(r3zip).hexdigest(),
                }}),encoding="utf-8")
            registry.chmod(0o600)
            cfg=auth_dir/"lan-auth.json"
            cfg.write_text(
                '{"username":"r3-fixture-user",'
                '"password":"synthetic-long-password-9999"}',encoding="utf-8")
            cfg.chmod(0o600)
            binary=bin_dir/"bob-activity-manager"
            binary.write_bytes(manager)
            (bin_dir/"navigation_shell.py").write_bytes(nav)
            env={**os.environ,
                "HOME":str(home),
                "PYTHONPATH":os.pathsep.join([
                    str(bin_dir),str(ROOT/"src/lib/bob"),str(ROOT/"src")]),
                "BOB_MANAGER_BIND":"0.0.0.0",
                "BOB_MANAGER_PORT":"18790",
                "PYTHONDONTWRITEBYTECODE":"1"}
            p=subprocess.run([sys.executable,"-c",CHILD,str(binary)],
                             cwd=root,env=env,timeout=20,
                             capture_output=True,text=True,check=False)
            self.assertEqual(p.returncode,0,p.stderr[-3000:])
            self.assertIn("LAN HTTP + exact Host/Origin/CSRF",p.stdout)

if __name__=="__main__":
    unittest.main()
