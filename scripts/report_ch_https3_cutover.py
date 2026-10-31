#!/usr/bin/env python3
"""CH-HTTPS3 exact OMEN cutover preflight and post-install TLS acceptance.

Read-only; no unit actions, cert generation, remote URLs, settings writes,
Moltbook traffic, CA signing key reads or publisher permissions. Post-install
proves a validated authenticated TLS connection AND refuses plaintext HTTP.
"""
from __future__ import annotations

from http.client import HTTPConnection, HTTPSConnection, HTTPException
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src"),str(ROOT/"src/lib/bob")]
import bob_release_updater as updater
import prepare_ch_https2 as certs
import report_ch_https1_installed as previous
import report_ch_https0 as host0
import report_r313d_host as old_host
import r313d_live_off_migration as migration

BEFORE="v0.8.0-chhttps1"
AFTER="v0.8.0-chhttps3"
CA_FINGERPRINT="af47c380af49eaf5b51683eb2cb1b6455eba019e754e09e295a0a3eeedc1f196"
EXPECTED_FILES=frozenset(("bob_manager_tls.py","bob-activity-manager",
                          "bob-release-updater","bob_r3_package.pyz",
                          "bob_r313d_web.py","bob_r313d_owner.py"))
ROUTES=("/r3",)
ADDRESS="127.0.0.1"
PORT=18790


def _ca_verified() -> bool:
    try:
        public=certs.TLS_DIR/"ca.crt"
        if not certs._owner_boundary() or not certs._private(public):
            return False
        if hashlib.sha256(public.read_bytes()).hexdigest()!=CA_FINGERPRINT:
            return False
        material=certs.verify_material(certs.TLS_DIR)
        return (material["certificate_chain"]=="verified"
                and material["public_ca_sha256"]==CA_FINGERPRINT
                and material["disposable_loopback_tls"]=="verified")
    except (OSError,ValueError,TypeError,KeyError,ssl.SSLError):
        return False


def _release_verified(release: str) -> bool:
    try:
        r=updater.registry()
        return (r["release"]==release
                and EXPECTED_FILES.issubset(r["files"])
                and updater.live_ok(r))
    except (OSError,TypeError,ValueError,KeyError):
        return False


def _host_source_off() -> bool:
    try:
        state=migration._db_review()
        return (state["state"]=="ready"
                and migration._journal_state()=="complete"
                and migration._host_phase_accepted(
                    old_host.collect(private_copy=False),
                    state,"complete"))
    except (OSError,TypeError,ValueError,KeyError):
        return False


def _manager_active() -> bool:
    return (host0._unit_state("bob-activity-manager.service","is-active")
            =="active")


def _timers_active() -> bool:
    return (
        host0._unit_state("bob-moltbook-publisher.timer","is-active")=="active"
        and host0._unit_state("bob-moltbook-scout.timer","is-active")=="active"
    )


def _https_route(path: str, *, authenticated: bool) -> tuple[int,bytes]:
    """Exactly the known IP/route; verified CA, no redirects or unsafe fallback."""
    if path not in ROUTES:
        raise ValueError("unreviewed_https_route")
    auth=updater.authorization() if authenticated else None
    conn=HTTPSConnection(ADDRESS,PORT,timeout=6,
                         context=updater.manager_tls_context())
    try:
        headers={"Host":"127.0.0.1:18790"}
        if auth is not None:
            headers["Authorization"]=auth
        conn.request("GET",path,headers=headers)
        res=conn.getresponse()
        body=res.read(65537)
        return res.status,body
    finally:
        conn.close()


def _authenticated_r3_https() -> bool:
    try:
        status,page=_https_route("/r3",authenticated=True)
        anon,body=_https_route("/r3",authenticated=False)
        return (status==200 and len(page)<=65536
                and b"Bob R3 Controls" in page
                and b"R3 automatic publishing" in page
                and b"compiled locked" in page
                and b"Owner controls remain unavailable" not in page
                and anon==401 and len(body)<=65536)
    except (OSError,ValueError,TypeError,ssl.SSLError,HTTPException):
        return False


def _plaintext_refused() -> bool:
    """No HTTP response of any status allowed on the TLS-only manager port."""
    conn=HTTPConnection(ADDRESS,PORT,timeout=3)
    try:
        conn.request("GET","/healthz",headers={"Host":"127.0.0.1:18790"})
        res=conn.getresponse()
        res.read(4097)
        return False
    except (OSError,TimeoutError,ssl.SSLError,HTTPException):
        return True
    finally:
        conn.close()


def inspect(phase: str) -> dict:
    if phase not in ("preflight","installed"):
        raise ValueError("ch_https3_unknown_phase")
    ready_manager=_manager_active()
    timers=_timers_active()
    source_off=_host_source_off()
    certificate=_ca_verified()
    release=_release_verified(BEFORE if phase=="preflight" else AFTER)
    proto=False
    authenticated="not_checked"
    plaintext="not_checked"
    old_health="not_checked"
    if phase=="preflight" and all(
            (release,ready_manager,timers,source_off,certificate)):
        old=previous.inspect()
        proto=(old["installation_acceptance"]=="PASS"
               and old["current_manager_transport"]=="http_pre_cutover")
        old_health="pass" if proto else "unverified"
    if phase=="installed" and all(
            (release,ready_manager,timers,source_off,certificate)):
        proto=(updater.manager_transport(AFTER)=="https"
               and updater.healthy(updater.authorization(),release=AFTER))
        authenticated=("pass" if _authenticated_r3_https()
                       else "unverified")
        plaintext=("refused" if _plaintext_refused() else "accepted_or_unverified")
    passed=(release and ready_manager and timers and source_off
            and certificate and proto and (
                old_health=="pass" if phase=="preflight" else
                authenticated=="pass" and plaintext=="refused"))
    return {
        "format":"bob-ch-https3-cutover-check-v1",
        "phase":phase,
        "installed_release":"verified" if release else "unverified",
        "r3_schema_journal_and_source_off":"verified" if source_off else "unverified",
        "manager_running":ready_manager,
        "scheduled_timers_unchanged_and_active":timers,
        "public_ca_sha256_matched":certificate,
        "old_authenticated_http_health":old_health,
        "authenticated_https_health":"pass" if phase=="installed" and proto
                else "not_checked" if phase=="preflight" else "unverified",
        "authenticated_r3_https":authenticated,
        "plain_http_on_old_port":plaintext,
        "acceptance":"PASS" if passed else "NOT_VERIFIED",
        "windows_client_trust":"owner_reported_separate_not_checked_by_script",
        "live_services_changed_by_check":False,
        "database_changed_by_check":False,
        "publisher_or_r3_permissions_changed_by_check":False,
        "r3_public_send_authorized":False,
    }


def main(args=None) -> int:
    argv=sys.argv[1:] if args is None else args
    if argv not in (["--preflight"],["--installed"],
                    ["--preflight","--json"],["--installed","--json"]):
        print("Usage: python3 scripts/report_ch_https3_cutover.py "
              "[--preflight | --installed] [--json]")
        return 2
    if os.geteuid()==0:
        print("CH-HTTPS3 read-only report refuses root")
        return 1
    phase=argv[0].lstrip("-")
    try:
        report=inspect(phase)
    except (OSError,ValueError,TypeError,KeyError,ssl.SSLError):
        report={"phase":phase,"acceptance":"NOT_VERIFIED",
                "r3_public_send_authorized":False}
    if "--json" in argv:
        print(json.dumps(report,sort_keys=True,indent=2))
    else:
        print("CH-HTTPS3 "+phase.upper()+" (READ ONLY)")
        for key in (
                "installed_release","r3_schema_journal_and_source_off",
                "manager_running","scheduled_timers_unchanged_and_active",
                "public_ca_sha256_matched","old_authenticated_http_health",
                "authenticated_https_health","authenticated_r3_https",
                "plain_http_on_old_port","acceptance"):
            print(key.replace("_"," ")+":",report.get(key,"unverified"))
        print("Live services or database modified by this report: NO")
        print("New R3 public posting rights: NONE")
    return 0 if report["acceptance"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
