#!/usr/bin/env python3
"""R4 consolidated signed installation acceptance. Read-only / no send.

Run ONLY after an eventual owner-approved, signed v0.8.0-autonomy1 install.
Never installs schema, starts services, modifies queues, approves proposals,
arms public requests, downloads code or initiates any Moltbook network call.
All HTTP probes target authenticated 127.0.0.1:18790 over private HTTPS.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bob_release_updater as updater

RELEASE="v0.8.0-autonomy1"
ROUTES=("/r4/now","/r4/inbox","/r4/bob",
        "/r4/controls","/r4/diagnostics")


def authenticated_r4_routes(auth) -> bool:
    try:
        if updater.manager_transport(RELEASE)!="https":
            return False
        for path in ROUTES:
            conn=updater._manager_connection(release=RELEASE,timeout=8)
            try:
                conn.request("GET",path,headers={
                    "Host":"127.0.0.1:18790","Authorization":auth})
                response=conn.getresponse()
                body=response.read(131073)
                if response.status!=200 or len(body)>131072:
                    return False
            finally:
                conn.close()
        return True
    except (OSError,ValueError,TypeError,RuntimeError):
        return False


def inspect()->dict:
    """No hidden fallback to HTTP or schema repair if candidate is absent."""
    out={
        "format":"r4-autonomy1-installed-v1","release":RELEASE,
        "signed_installed_source":False,
        "legacy_and_r3_registry":False,
        "authenticated_https":False,
        "new_r4_routes":False,
        "versioned_additive_schema":False,
        "publisher_inactive_at_check":False,
        "new_r4_actions_attempted":None,
        "public_send_armed_by_report":False,
        "database_changed_by_report":False,
        "production_migration_performed_by_report":False,
    }
    try:
        installed=updater.registry()
        if installed["release"]!=RELEASE or not updater.live_ok(installed):
            return out
        if updater.manager_transport(RELEASE)!="https":
            return out
        # These modules are installed source, not arbitrary checkout imports.
        sys.path.insert(0,str(updater.BIN))
        try:
            import bob_r4_installed_gate as gate
            from bob_r4_outbox import schema_ready as outbox_ready
            if not gate.verify():
                return out
            out["signed_installed_source"]=True
            out["legacy_and_r3_registry"]=all(
                name in installed["files"] for name in (
                    "bob_v08_package.pyz","bob_r3_package.pyz",
                    "bob-moltbook-publisher"))
            source=updater.DB
            if source.is_symlink() or not source.is_file():
                return out
            uri=source.as_uri()+"?mode=ro"
            with closing(sqlite3.connect(uri,uri=True,timeout=6)) as db:
                db.execute("PRAGMA query_only=ON")
                schema=updater.installed_r4_schema_module()
                out["versioned_additive_schema"]=(schema.inspect(db)=="ready"
                    and outbox_ready(db))
                if out["versioned_additive_schema"]:
                    out["new_r4_actions_attempted"]=db.execute(
                        "SELECT COUNT(*) FROM r4_action_outbox "
                        "WHERE attempted_at IS NOT NULL").fetchone()[0]
        finally:
            sys.path.remove(str(updater.BIN))
        out["publisher_inactive_at_check"]=updater.r4_publisher_inactive()
        auth=updater.authorization()
        out["authenticated_https"]=updater.healthy(auth,release=RELEASE)
        if out["authenticated_https"]:
            out["new_r4_routes"]=authenticated_r4_routes(auth)
    except (OSError,ValueError,TypeError,sqlite3.Error,ImportError,
            RuntimeError,KeyError,AttributeError):
        return out
    return out


def main(argv=None)->int:
    args=sys.argv[1:] if argv is None else argv
    if args!=["--check"]:
        print("Usage: python3 scripts/report_r4_installed.py --check")
        return 2
    data=inspect()
    ok=(data["signed_installed_source"] and
        data["legacy_and_r3_registry"] and
        data["authenticated_https"] and data["new_r4_routes"] and
        data["versioned_additive_schema"] and
        data["publisher_inactive_at_check"] and
        data["new_r4_actions_attempted"]==0)
    data["acceptance"]="PASS" if ok else "REFUSED_OR_NOT_INSTALLED"
    print(json.dumps(data,sort_keys=True,separators=(",",":")))
    return 0 if ok else 1


if __name__=="__main__":
    raise SystemExit(main())
