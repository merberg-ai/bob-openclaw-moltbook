#!/usr/bin/env python3
"""CH-HTTPS0 fixed-OMEN read-only TLS cutover inventory.

No filesystem writes, service changes, private key reads, credential output,
external network requests, Moltbook calls or R3 owner mutations. This is a
read-only predecessor to independently reviewed TLS-aware updater and manager
releases. It cannot enable TLS or authenticate a new browser.
"""
from __future__ import annotations

from http.client import HTTPConnection
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import socket
import stat
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src"),str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import r313d_live_off_migration as migration

LAN_IP="192.168.1.24"
PORT=18790
TLS_DIR=Path.home()/".config/bob-system/manager-tls"
TLS_NAMES=("ca.crt","server.crt","server.key")
UNITS=("bob-activity-manager.service","bob-moltbook-publisher.timer",
       "bob-moltbook-scout.timer")


def _fixed_account() -> bool:
    try:
        return (os.geteuid()!=0
                and pwd.getpwuid(os.geteuid()).pw_dir==str(Path.home())
                and ipaddress.ip_address(LAN_IP).is_private)
    except (OSError,KeyError,ValueError):
        return False


def _unit_state(unit: str, action: str) -> str:
    if unit not in UNITS or action not in ("is-active","is-enabled"):
        raise ValueError("unreviewed_unit_or_operation")
    try:
        result=subprocess.run(
            ["systemctl","--user",action,unit],
            capture_output=True,text=True,timeout=5,check=False)
        value=result.stdout.strip()
        if value in ("active","inactive","enabled","disabled","static"):
            return value
    except (OSError,ValueError,subprocess.TimeoutExpired):
        pass
    return "unverified"


def _listener() -> str:
    """No network scan. Inspect only the installed local listening socket."""
    try:
        result=subprocess.run(
            ["ss","-ltnH","sport = :18790"],
            capture_output=True,text=True,timeout=5,check=False)
        if result.returncode:
            return "unverified"
        rows=result.stdout.splitlines()
        if any(re.search(r"(?:0\.0\.0\.0|\*|\[::\]):18790(?:\s|$)",line)
               for line in rows):
            return "lan_or_wildcard"
        if any(re.search(r"(?:127\.0\.0\.1|\[::1\]):18790(?:\s|$)",line)
               for line in rows):
            return "loopback_only"
        return "other" if rows else "not_listening"
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return "unverified"


def _private_dir(path: Path) -> bool:
    try:
        row=path.lstat()
        return (stat.S_ISDIR(row.st_mode)
                and row.st_uid==os.geteuid()
                and not row.st_mode & 0o077)
    except OSError:
        return False


def _materials() -> str:
    """Metadata only. Never open TLS private keys or print cert contents."""
    files=[TLS_DIR/name for name in TLS_NAMES]
    if not TLS_DIR.exists() and not TLS_DIR.is_symlink():
        return "not_prepared"
    if not _private_dir(TLS_DIR):
        return "untrusted"
    if not all(p.exists() and not p.is_symlink() for p in files):
        return "incomplete"
    try:
        for path in files:
            row=path.lstat()
            if (not stat.S_ISREG(row.st_mode)
                    or row.st_uid!=os.geteuid()
                    or row.st_nlink!=1
                    or row.st_mode & 0o077
                    or not 1<=row.st_size<=32768):
                return "untrusted"
        return "present_needs_certificate_validation"
    except OSError:
        return "untrusted"


def _loopback_http() -> str:
    """Authenticated fixed localhost GET only; no response body exposed."""
    try:
        auth=updater.authorization()
        con=HTTPConnection("127.0.0.1",PORT,timeout=5)
        try:
            con.request("GET","/r3",headers={
                "Host":"127.0.0.1:18790","Authorization":auth})
            response=con.getresponse()
            payload=response.read(65537)
            if response.status==200 and len(payload)<=65536 and (
                    b"Bob R3 Controls" in payload
                    and b"R3 automatic publishing" in payload
                    and b"compiled locked" in payload
                    and b"Owner controls remain unavailable" not in payload):
                return "authenticated_http_r3"
            return "not_verified"
        finally:
            con.close()
    except (OSError,ValueError,KeyError,socket.timeout):
        return "not_verified"


def evaluate(observations: dict) -> dict:
    """Pure fail-closed decision; metadata only, never a TLS activation."""
    correct=(observations.get("account")=="expected_openclaw"
        and observations.get("installed_release")=="v0.8.0-r3stage1"
        and observations.get("r3_schema")=="ready"
        and observations.get("migration_journal")=="complete"
        and observations.get("r3_dispatch_authorized") is False
        and observations.get("manager_service")=="active"
        and observations.get("publisher_timer")=="active"
        and observations.get("scout_timer")=="active"
        and observations.get("current_manager_transport")=="authenticated_http_r3")
    return {
        "format":"bob-ch-https0-readiness-v1",
        **observations,
        "existing_transport":"http_lan_not_secure",
        "target_transport":"https_only_same_lan_port",
        "candidate_certificate_state":observations.get(
            "certificate_state","unverified"),
        "source_preflight":"pass" if correct else "needs_review",
        "next_reviewed_phase":"tls_aware_updater_before_any_tls_cutover"
            if correct else "resolve_preflight_blockers",
        "windows_browser_ca_trust":"not_checked_on_host",
        "live_service_changes":0,
        "live_database_changes":0,
        "new_r3_send_rights":False,
        "tls_activated":False,
    }


def collect() -> dict:
    if not _fixed_account():
        return evaluate({"account":"unverified"})
    try:
        record=updater.registry()
        installed=("v0.8.0-r3stage1" if
                   record["release"]=="v0.8.0-r3stage1"
                   and updater.live_ok(record) else "unverified")
    except (OSError,ValueError,KeyError,TypeError):
        installed="unverified"
    try:
        schema=migration._db_review()
        journal=migration._journal_state()
        ready=migration._owner_installed_gate()
    except (OSError,ValueError,KeyError,TypeError):
        schema={"state":"refused"}
        journal="untrusted"
        ready=False
    data={
        "account":"expected_openclaw",
        "installed_release":installed if ready else "unverified",
        "r3_schema":schema.get("state"),
        "migration_journal":journal,
        "r3_dispatch_authorized":False,
        "manager_service":_unit_state(UNITS[0],"is-active"),
        "publisher_timer":_unit_state(UNITS[1],"is-active"),
        "scout_timer":_unit_state(UNITS[2],"is-active"),
        "current_manager_transport":_loopback_http(),
        "listener":_listener(),
        "certificate_state":_materials(),
        "tls_backend":"python_stdlib_ssl_reviewed_candidate",
        "lan_ipv4":LAN_IP,
        "manager_port":PORT,
    }
    return evaluate(data)


def main(argv=None) -> int:
    argv=sys.argv[1:] if argv is None else argv
    if argv not in ([],["--json"]):
        print("Usage: python3 scripts/report_ch_https0.py [--json]")
        return 2
    report=collect()
    if argv==["--json"]:
        print(json.dumps(report,sort_keys=True,indent=2))
    else:
        print("CH-HTTPS0 ACTIVITY MANAGER SECURITY READINESS (READ ONLY)")
        for key in ("installed_release","r3_schema","migration_journal",
                    "manager_service","publisher_timer","scout_timer",
                    "current_manager_transport","listener","certificate_state",
                    "source_preflight","next_reviewed_phase"):
            print(key.replace("_"," ")+":",report.get(key,"unverified"))
        print("Current HTTP LAN credentials encrypted: NO")
        print("Target: HTTPS-only on existing LAN 192.168.1.24:18790")
        print("browser CA trusted: NOT VERIFIED")
        print("live files/services/database changed: NO")
        print("R3 real publishing enabled: NO")
    return 0 if report["source_preflight"]=="pass" else 1


if __name__=="__main__":
    raise SystemExit(main())
