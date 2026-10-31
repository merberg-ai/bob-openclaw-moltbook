"""CH-HTTPS3 verified TLS-only transport for installed Bob Activity Manager.

No network/client code, credentials, publisher, queue or schema operations.
The existing user systemd unit and port are unchanged. This module is useful
only as part of the separately reviewed release-pinned manager executable.
"""
from __future__ import annotations

from http.server import ThreadingHTTPServer
from pathlib import Path
import os
import pwd
import ssl
import stat
import subprocess
from urllib.parse import urlsplit

HOME=Path.home()
CONFIG=HOME/".config/bob-system"
TLS_DIR=CONFIG/"manager-tls"
CA=TLS_DIR/"ca.crt"
CERT=TLS_DIR/"server.crt"
KEY=TLS_DIR/"server.key"
OPENSSL=Path("/usr/bin/openssl")
EXPECTED_LAN_IP="192.168.1.24"


def _private(path: Path, directory: bool=False):
    info=path.lstat()  # rejects symlinks by checking exact type
    valid=stat.S_ISDIR if directory else stat.S_ISREG
    return (valid(info.st_mode) and info.st_uid==os.geteuid()
            and not stat.S_IMODE(info.st_mode)&0o077
            and (directory or info.st_nlink==1))


def _verified_material():
    """Fixed owner-only paths, matching private CA, SAN and server identity."""
    if (os.geteuid()==0
            or pwd.getpwuid(os.geteuid()).pw_dir!=str(HOME)
            or pwd.getpwuid(os.geteuid()).pw_name!="openclaw"):
        raise ValueError("ch_https3_wrong_service_account")
    for directory in (CONFIG,TLS_DIR):
        if not _private(directory,directory=True):
            raise ValueError("ch_https3_untrusted_tls_directory")
    for name in (CA,CERT,KEY):
        if not _private(name) or not 1<=name.stat().st_size<=32768:
            raise ValueError("ch_https3_untrusted_tls_material")
    info=OPENSSL.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid!=0
            or info.st_mode&0o022):
        raise ValueError("ch_https3_untrusted_cert_validator")
    commands=(
        ("x509","-in",str(CERT),"-noout","-checkend","2592000"),
        ("verify","-CAfile",str(CA),"-purpose","sslserver",
         "-verify_ip",EXPECTED_LAN_IP,str(CERT)),
        ("verify","-CAfile",str(CA),"-purpose","sslserver",
         "-verify_ip","127.0.0.1",str(CERT)),
        ("verify","-CAfile",str(CA),"-purpose","sslserver",
         "-verify_hostname","localhost",str(CERT)),
    )
    for args in commands:
        answer=subprocess.run(
            [str(OPENSSL),*args],
            capture_output=True,timeout=8,check=False,
            env={"PATH":"/usr/bin:/bin","LANG":"C"})
        if answer.returncode:
            raise ValueError("ch_https3_tls_chain_or_san_unverified")


def tls_context():
    """No client cert or plaintext fallback; key loaded only after validation."""
    _verified_material()
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.options |= ssl.OP_NO_COMPRESSION
    context.load_cert_chain(certfile=str(CERT),keyfile=str(KEY))
    return context


class HTTPSOnlyHandlerMixin:
    """Use existing exact Host, LAN Basic auth and CSRF; enforce HTTPS origins."""

    def _valid_host(self):
        return (isinstance(self.connection,ssl.SSLSocket)
                and super()._valid_host())

    def _valid_origin(self):
        """Match the current manager policy, but require the true HTTPS peer.

        Never trust X-Forwarded-Proto, caller mode, synthetic request headers
        or any Origin for a different scheme/host. Preserve the existing
        opaque-Origin handling only with no contradictory Fetch Metadata.
        """
        if not self._valid_host():
            return False
        host=self.headers.get("Host","")
        origin=self.headers.get("Origin")
        fetch=self.headers.get("Sec-Fetch-Site","").lower()
        if fetch=="cross-site":
            return False
        if origin in (None,"null"):
            if fetch not in ("","same-origin","none"):
                return False
            referer=self.headers.get("Referer","")
            if referer:
                url=urlsplit(referer)
                if url.scheme!="https" or url.netloc!=host:
                    return False
            return True
        return origin=="https://"+host

    def end_headers(self):
        # A browser may ignore HSTS for an IP, but never send a plaintext
        # downgrade or advertise a false proxy scheme.
        self.send_header("Strict-Transport-Security","max-age=31536000")
        super().end_headers()


def serve_tls(handler,host,port):
    """Context and certificate are checked BEFORE binding the listening port."""
    context=tls_context()
    with ThreadingHTTPServer((host,port),handler) as server:
        server.socket=context.wrap_socket(server.socket,server_side=True)
        print("Bob Activity Manager TLS-only listening on %s:%s" %
              (host,server.server_port),flush=True)
        server.serve_forever()
