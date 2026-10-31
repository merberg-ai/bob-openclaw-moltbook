#!/usr/bin/env python3
"""CH-HTTPS2: owner-controlled private CA and TLS leaf provisioning for Bob.

Read-only by default. --apply requires exact owner TTY confirmation; writes
ONLY brand-new private certificate directory under the fixed Bob config home.
No dashboard, Windows trust, publishing, service, registry or SQLite changes.
"""
from __future__ import annotations

import hashlib
from http.client import HTTPSConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src"),str(ROOT/"src/lib/bob")]
import report_ch_https1_installed as installed

HOME=Path.home()
CONFIG_DIR=HOME/".config/bob-system"
TLS_DIR=CONFIG_DIR/"manager-tls"
OPENSSL=Path("/usr/bin/openssl")
LAN_IP="192.168.1.24"
NAMES=("ca.key","ca.crt","server.key","server.csr","server.crt")
PUBLIC=("ca.crt","server.crt")
CA_DAYS=1825
LEAF_DAYS=365

CA_CONF="""[req]
prompt = no
distinguished_name = dn
x509_extensions = v3_ca
[dn]
CN = Bob Activity Manager Private Root
[v3_ca]
basicConstraints = critical,CA:TRUE,pathlen:0
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
"""
SERVER_CONF="""[req]
prompt = no
distinguished_name = dn
req_extensions = v3_server
[dn]
CN = Bob Activity Manager LAN
[v3_server]
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = @san
[san]
IP.1 = 192.168.1.24
IP.2 = 127.0.0.1
DNS.1 = localhost
"""


def _private(path: Path, *, directory=False) -> bool:
    try:
        row=path.lstat()
        typ=stat.S_ISDIR if directory else stat.S_ISREG
        return (typ(row.st_mode) and row.st_uid==os.geteuid()
                and not stat.S_IMODE(row.st_mode)&0o077
                and (directory or row.st_nlink==1))
    except OSError:
        return False


def _owner_boundary() -> bool:
    try:
        return (os.geteuid()!=0
                and pwd.getpwuid(os.geteuid()).pw_dir==str(HOME)
                and pwd.getpwuid(os.geteuid()).pw_name=="openclaw"
                and _private(CONFIG_DIR,directory=True)
                and OPENSSL.is_file() and not OPENSSL.is_symlink()
                and OPENSSL.stat().st_uid==0
                and not OPENSSL.stat().st_mode&0o022)
    except (OSError,KeyError):
        return False


def _already_present() -> str:
    if not TLS_DIR.exists() and not TLS_DIR.is_symlink():
        return "absent"
    if not _private(TLS_DIR,directory=True):
        return "untrusted"
    return "existing_do_not_overwrite"


def _cmd(argv: list[str], *, cwd: Path) -> bytes:
    """No shell, no user-provided commands, no stdout or key data displayed."""
    result=subprocess.run([str(OPENSSL),*argv],cwd=cwd,
                          capture_output=True,timeout=20,check=False,
                          env={"PATH":"/usr/bin:/bin","LANG":"C"})
    if result.returncode or len(result.stdout)>32768:
        raise ValueError("ch_https2_openssl_operation_refused")
    return result.stdout


def verify_material(root: Path) -> dict:
    """Read metadata; verify three exact SANs and distinct root/server keys."""
    if not _private(root,directory=True):
        raise ValueError("ch_https2_private_directory_required")
    for name in ("ca.key","ca.crt","server.key","server.crt"):
        file=root/name
        if not _private(file) or not 1<=file.stat().st_size<=32768:
            raise ValueError("ch_https2_private_file_required")
    ca=root/"ca.crt"
    for name in ("ca.crt","server.crt"):
        _cmd(["x509","-in",name,"-noout","-checkend","2592000"],cwd=root)
    _cmd(["verify","-CAfile","ca.crt","-purpose","sslserver",
          "-verify_ip",LAN_IP,"server.crt"],cwd=root)
    _cmd(["verify","-CAfile","ca.crt","-purpose","sslserver",
          "-verify_ip","127.0.0.1","server.crt"],cwd=root)
    _cmd(["verify","-CAfile","ca.crt","-purpose","sslserver",
          "-verify_hostname","localhost","server.crt"],cwd=root)
    pub_cert=_cmd(["x509","-in","server.crt","-pubkey","-noout"],cwd=root)
    pub_key=_cmd(["pkey","-in","server.key","-pubout"],cwd=root)
    if pub_cert!=pub_key:
        raise ValueError("ch_https2_server_key_mismatch")
    root_txt=_cmd(["x509","-in","ca.crt","-noout","-text"],cwd=root)
    leaf_txt=_cmd(["x509","-in","server.crt","-noout","-text"],cwd=root)
    if (b"CA:TRUE" not in root_txt or b"Certificate Sign" not in root_txt
            or b"CA:FALSE" not in leaf_txt
            or b"TLS Web Server Authentication" not in leaf_txt):
        raise ValueError("ch_https2_certificate_roles_not_verified")
    if b"CA:TRUE" in leaf_txt:
        raise ValueError("ch_https2_server_ca_role_invalid")
    _local_tls_smoke(root)
    return {
        "certificate_chain":"verified",
        "lan_ip_san":"192.168.1.24_verified",
        "loopback_ip_san":"127.0.0.1_verified",
        "localhost_san":"localhost_verified",
        "key_match":"verified",
        "private_permissions":"verified",
        "disposable_loopback_tls":"verified",
        "public_ca_file":str(ca),
        "public_ca_sha256":hashlib.sha256(ca.read_bytes()).hexdigest(),
        "private_keys_exported":False,
    }


class _SmokeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path!="/healthz":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length","2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_args):
        pass


class _SilentServer(HTTPServer):
    def handle_error(self, *_args):
        pass


def _local_tls_smoke(root: Path) -> None:
    """Tiny synthetic local-only HTTPS socket, not Bob's live port."""
    srv=_SilentServer(("127.0.0.1",0),_SmokeHandler)
    server_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.minimum_version=ssl.TLSVersion.TLSv1_2
    server_context.load_cert_chain(str(root/"server.crt"),str(root/"server.key"))
    srv.socket=server_context.wrap_socket(srv.socket,server_side=True)
    thread=threading.Thread(target=srv.serve_forever,daemon=True)
    thread.start()
    try:
        client_context=ssl.create_default_context(cafile=str(root/"ca.crt"))
        client_context.minimum_version=ssl.TLSVersion.TLSv1_2
        conn=HTTPSConnection("127.0.0.1",srv.server_port,
                             timeout=3,context=client_context)
        try:
            conn.request("GET","/healthz")
            response=conn.getresponse()
            if response.status!=200 or response.read(3)!=b"ok":
                raise ValueError("ch_https2_synthetic_tls_response_invalid")
        finally:
            conn.close()
        try:
            with socket.create_connection(("127.0.0.1",srv.server_port),timeout=3) as raw:
                with client_context.wrap_socket(raw,server_hostname="wrong.example.invalid"):
                    raise ValueError("ch_https2_hostname_validation_bypassed")
        except ssl.SSLCertVerificationError:
            pass
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=3)


def _generate(root: Path) -> dict:
    if not _private(root,directory=True):
        raise ValueError("ch_https2_staging_not_private")
    (root/"ca.cnf").write_text(CA_CONF,encoding="ascii")
    (root/"server.cnf").write_text(SERVER_CONF,encoding="ascii")
    for file in (root/"ca.cnf",root/"server.cnf"):
        file.chmod(0o600)
    _cmd(["genpkey","-algorithm","EC","-pkeyopt","ec_paramgen_curve:P-256",
          "-out","ca.key"],cwd=root)
    _cmd(["req","-new","-x509","-sha256","-days",str(CA_DAYS),
          "-key","ca.key","-config","ca.cnf","-out","ca.crt"],cwd=root)
    _cmd(["genpkey","-algorithm","EC","-pkeyopt","ec_paramgen_curve:P-256",
          "-out","server.key"],cwd=root)
    _cmd(["req","-new","-sha256","-key","server.key",
          "-config","server.cnf","-out","server.csr"],cwd=root)
    serial="0x"+secrets.token_hex(16)
    _cmd(["x509","-req","-sha256","-days",str(LEAF_DAYS),
          "-in","server.csr","-CA","ca.crt","-CAkey","ca.key",
          "-set_serial",serial,"-extfile","server.cnf",
          "-extensions","v3_server","-out","server.crt"],cwd=root)
    for file in root.iterdir():
        if file.is_symlink() or not file.is_file():
            raise ValueError("ch_https2_generated_artifact_invalid")
        file.chmod(0o600)
    summary=verify_material(root)
    for name in ("server.csr","ca.cnf","server.cnf"):
        (root/name).unlink()
    return summary


def _installed_gate() -> bool:
    """Exact accepted pre-cutover installation; no service state change."""
    report=installed.inspect()
    return (report.get("installation_acceptance")=="PASS"
            and report.get("installed_release")=="verified"
            and report.get("r3_off_source_gates")=="verified"
            and report.get("r3_schema")=="ready"
            and report.get("migration_journal")=="complete"
            and report.get("current_manager_transport")=="http_pre_cutover")


def preflight() -> dict:
    owner=_owner_boundary()
    state=_already_present()
    installed_ok=_installed_gate() if owner else False
    return {
        "format":"bob-ch-https2-private-cert-v1",
        "owner_host":"verified" if owner else "unverified",
        "ch_https1_install":"verified" if installed_ok else "unverified",
        "certificate_state":state,
        "eligible_to_prepare":bool(owner and installed_ok and state=="absent"),
        "current_manager_transport":"http_unchanged",
        "manager_services_changed":False,
        "certificate_files_changed":False,
        "windows_trust_changed":False,
        "r3_dispatch_authorized":False,
    }


def apply() -> dict:
    first=preflight()
    if not first["eligible_to_prepare"]:
        raise ValueError("ch_https2_preflight_not_eligible")
    root=Path(tempfile.mkdtemp(prefix=".manager-tls-",dir=CONFIG_DIR))
    root.chmod(0o700)
    try:
        summary=_generate(root)
        if not _owner_boundary() or _already_present()!="absent":
            raise ValueError("ch_https2_boundary_changed_during_generation")
        os.rename(root,TLS_DIR)
        summary["public_ca_file"]=str(TLS_DIR/"ca.crt")
        return summary
    finally:
        if root.exists():
            shutil.rmtree(root)


def verify_current() -> dict:
    """Read-only post-provision chain, SAN, key and local TLS acceptance."""
    if (not _owner_boundary() or not _installed_gate()
            or not _private(TLS_DIR,directory=True)):
        raise ValueError("ch_https2_verification_boundary_not_met")
    return verify_material(TLS_DIR)


def main(args=None) -> int:
    opts=sys.argv[1:] if args is None else args
    if opts not in ([],["--json"],["--apply"],["--verify"]):
        print("Usage: python3 scripts/prepare_ch_https2.py [--json | --apply | --verify]")
        return 2
    if os.geteuid()==0:
        print("CH-HTTPS2: REFUSED (run as openclaw, not root)")
        return 1
    try:
        if opts==["--verify"]:
            result=verify_current()
            print("CH-HTTPS2 CERTIFICATE ACCEPTANCE: PASS (READ ONLY)")
            print("private CA/server chain, three SANs, key and TLS handshake: VERIFIED")
            print("public CA file:",result["public_ca_file"])
            print("public CA SHA256:",result["public_ca_sha256"])
            print("Windows browser trust: STILL SEPARATE")
            print("Activity Manager still HTTP: YES")
            print("R3 real publishing authorized: NO")
            return 0
        if opts==["--apply"]:
            if not preflight()["eligible_to_prepare"]:
                raise ValueError("ch_https2_preflight_not_eligible")
            if not sys.stdin.isatty() or input(
                    "Type PREPARE BOB HTTPS to create private local CA/server cert (NO SERVICE CHANGE): "
            )!="PREPARE BOB HTTPS":
                raise ValueError("ch_https2_owner_confirmation_missing")
            summary=apply()
            print("CH-HTTPS2 PRIVATE CERTIFICATES: PREPARED")
            print("server SANs: 192.168.1.24, 127.0.0.1, localhost")
            print("local TLS handshake and hostname mismatch rejection: PASS")
            print("public CA path:",summary["public_ca_file"])
            print("public CA SHA256:",summary["public_ca_sha256"])
            print("Windows browser trust: NOT CONFIGURED")
            print("Activity Manager still HTTP: YES")
            print("R3 publication authorized: NO")
            return 0
        report=preflight()
        if opts==["--json"]:
            print(json.dumps(report,sort_keys=True,indent=2))
        else:
            print("CH-HTTPS2 PRIVATE CERTIFICATE PREFLIGHT (READ ONLY)")
            for key in ("owner_host","ch_https1_install",
                        "certificate_state","eligible_to_prepare"):
                print(key.replace("_"," ")+":",report[key])
            print("Activity Manager HTTPS active: NO")
            print("Live service, database or credential changes: NONE")
        return 0 if report["eligible_to_prepare"] else 1
    except (OSError,ValueError,TypeError,ssl.SSLError,subprocess.TimeoutExpired):
        print("CH-HTTPS2: REFUSED (inspect local private cert directory; no retry by overwrite)")
        return 1


if __name__=="__main__":
    raise SystemExit(main())
