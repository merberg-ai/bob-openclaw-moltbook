#!/usr/bin/env python3
"""Recover the proven-baseline v0.7.2 queue update incident and patch updater.

One explicit, guarded repair. No service restart or database writes. Keeps
the failed release transaction archive in place; uses a DIFFERENT release ID
for the next normal bobctl update. Read-only by default.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys

import bob_release_updater as engine

BASE = Path(__file__).resolve().parents[1]
OLD = BASE / "release_baselines/v072-queues1-incident/bob_release_updater.py"
NEW = BASE / "scripts/bob_release_updater.py"
FIRST_RELEASE = "v0.7.2-queues1"
RETRY_RELEASE = "v0.7.2-queues1-r1"
BASELINE_RELEASE = "v0.7.2-main-channel"
EXPECTED_FILES = {"bob_dashboard_manage.py", "bob-activity-manager", "navigation_shell.py"}
REPAIR_DIR = engine.STATE_DIR / "repair-queues1-incident"
REPAIR_STATUS = REPAIR_DIR / "status.json"
APPROVAL = "RECONCILE-BOB-QUEUE-INCIDENT"
RECOVERY_APPROVAL = "RESTORE-BOB-QUEUE-REPAIR"
FORMAT = "bob-queues1-reconciliation-v1"
HEX = re.compile(r"[0-9a-f]{64}\Z")


def checked_blob(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 524288:
        raise ValueError("untrusted updater release bytes")
    data = path.read_bytes()
    compile(data, str(path), "exec")
    return data


def read_private(path):
    engine.safe_private(path)
    if path.stat().st_size > 524288:
        raise ValueError("oversized private recovery file")
    return path.read_bytes()


def read_metadata(path):
    content = read_private(path)
    if len(content) > 32768:
        raise ValueError("oversized transaction metadata")
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("invalid transaction metadata")
    return data


def state(journal=None):
    info = read_metadata(REPAIR_STATUS)
    if set(info) != {"format", "phase"} or info["format"] != FORMAT:
        raise ValueError("unexpected repair state")
    if info["phase"] not in ("prepared", "complete", "restored", "incident"):
        raise ValueError("invalid repair phase")
    return info["phase"]


def save_phase(value):
    engine.save_private(REPAIR_STATUS, json.dumps(
        {"format": FORMAT, "phase": value}, sort_keys=True).encode() + b"\n")


def plan():
    """Read-only exact baseline and incident-archive verification."""
    folder = engine.checkout_from_config()
    if folder != BASE or engine.BRANCH != "main":
        raise ValueError("unexpected trusted main checkout")
    current = engine.registry()
    release = engine.manifest(folder)
    if current["release"] != BASELINE_RELEASE or not engine.live_ok(current):
        raise ValueError("installed code differs from registered baseline")
    if (release["release"] != RETRY_RELEASE or release["from"] != BASELINE_RELEASE
            or not release["restart_manager"]
            or {item["name"] for item in release["files"]} != EXPECTED_FILES):
        raise ValueError("unexpected reviewed retry manifest")
    journal = engine.read_journal()
    if (not journal or journal.get("release") != FIRST_RELEASE
            or journal.get("phase") != "incident"
            or journal.get("restart_manager") is not True):
        raise ValueError("not the expected original incident")
    old, new = checked_blob(OLD), checked_blob(NEW)
    target = engine.BIN / "bob-release-updater"
    if (target.is_symlink() or not target.is_file()
            or target.stat().st_uid != os.getuid() or target.read_bytes() != old
            or current["files"].get("bob-release-updater") != engine.digest(old)):
        raise ValueError("installed updater is not the pinned old version")
    if old == new or b"def wait_for_health(" not in new or b'BRANCH = "main"' not in new:
        raise ValueError("reviewed updater repair is missing")
    tx = engine.STATE_DIR / ("tx-" + FIRST_RELEASE)
    engine.safe_private(tx, directory=True)
    originals = read_metadata(tx / "original.json")
    candidates = read_metadata(tx / "candidate.json")
    before = read_metadata(tx / "registry-before.json")
    if (before != current or set(originals) != EXPECTED_FILES
            or set(candidates) != EXPECTED_FILES):
        raise ValueError("original transaction not linked to installed baseline")
    # The new release differs in ID only; its actual application bytes must
    # exactly match the failed transaction's candidate archive.
    for entry in release["files"]:
        name = entry["name"]
        original_sha = originals[name]
        new_sha = candidates[name]
        if not isinstance(new_sha, str) or not HEX.fullmatch(new_sha):
            raise ValueError("bad archived candidate digest")
        if engine.digest(engine.release_bytes(folder, entry)) != new_sha:
            raise ValueError("retry candidate differs from failed archive")
        live = engine.BIN / name
        if original_sha == "absent":
            if live.exists() or live.is_symlink() or (tx / ("old-" + name)).exists():
                raise ValueError("new module is not absent after rollback")
        else:
            if not isinstance(original_sha, str) or not HEX.fullmatch(original_sha):
                raise ValueError("bad archived baseline digest")
            previous = read_private(tx / ("old-" + name))
            if (engine.digest(previous) != original_sha or live.is_symlink()
                    or not live.is_file() or live.stat().st_uid != os.getuid()
                    or engine.digest(live.read_bytes()) != original_sha):
                raise ValueError("original application file not restored")
    if not engine.healthy(engine.authorization()):
        raise ValueError("authenticated dashboard baseline is not healthy")
    revised = json.loads(json.dumps(current))
    revised["files"]["bob-release-updater"] = engine.digest(new)
    archive_bytes = {
        "old-updater": old,
        "old-registry": read_private(engine.REGISTRY),
        "old-journal": read_private(engine.JOURNAL),
    }
    return old, new, revised, archive_bytes


def repair():
    if REPAIR_DIR.exists() or REPAIR_DIR.is_symlink():
        raise ValueError("existing repair transaction requires inspection")
    old, new, revised, archive = plan()
    # Revalidation under the updater's own cross-process lock.
    fd = engine.locked()
    try:
        plan()
        engine.private_dir(REPAIR_DIR)
        for name, contents in archive.items():
            engine.save_private(REPAIR_DIR / name, contents)
        save_phase("prepared")
        try:
            engine.write_target("bob-release-updater", new)
            engine.save_private(engine.REGISTRY,
                                json.dumps(revised, sort_keys=True).encode() + b"\n")
            original_journal = json.loads(archive["old-journal"])
            engine.store_journal({
                **original_journal, "phase": "rolled_back",
                "reconciled_from": "incident",
                "incident_archive_kept": "tx-" + FIRST_RELEASE,
            })
            if (not engine.live_ok(revised) or
                    engine.read_journal().get("phase") != "rolled_back" or
                    not engine.healthy(engine.authorization())):
                raise RuntimeError("reconciliation verification refused")
            save_phase("complete")
            return "baseline_reconciled_updater_patched"
        except (OSError, ValueError, RuntimeError):
            try:
                restore_from_archive(allowed_phases=("prepared",))
            except (OSError, ValueError, RuntimeError, KeyError, TypeError):
                save_phase("incident")
                raise RuntimeError("repair rollback incident; manual inspection needed") from None
            return "repair_rolled_back"
    finally:
        os.close(fd)


def restore_from_archive(*, allowed_phases):
    engine.safe_private(REPAIR_DIR, directory=True)
    if state() not in allowed_phases:
        raise ValueError("no recoverable pending repair")
    old = read_private(REPAIR_DIR / "old-updater")
    old_registry_bytes = read_private(REPAIR_DIR / "old-registry")
    old_journal_bytes = read_private(REPAIR_DIR / "old-journal")
    new = checked_blob(NEW)
    old_registry = json.loads(old_registry_bytes)
    if (old != checked_blob(OLD)
            or old_registry.get("release") != BASELINE_RELEASE):
        raise ValueError("repair snapshot does not match sealed baseline")
    new_registry = json.loads(json.dumps(old_registry))
    new_registry["files"]["bob-release-updater"] = engine.digest(new)
    new_registry_bytes = json.dumps(new_registry, sort_keys=True).encode() + b"\n"
    path = engine.BIN / "bob-release-updater"
    if path.is_symlink() or not path.is_file() or path.read_bytes() not in (old,new):
        raise ValueError("updater changed outside the repair")
    if engine.REGISTRY.is_symlink() or read_private(engine.REGISTRY) not in (
            old_registry_bytes, new_registry_bytes):
        raise ValueError("registry changed outside repair")
    journal = read_metadata(engine.JOURNAL)
    initial_journal = json.loads(old_journal_bytes)
    if journal not in (
            initial_journal,
            {**initial_journal, "phase": "rolled_back",
             "reconciled_from": "incident",
             "incident_archive_kept": "tx-" + FIRST_RELEASE}):
        raise ValueError("journal changed outside repair")
    # All validation precedes every write.
    engine.write_target("bob-release-updater", old)
    engine.save_private(engine.REGISTRY, old_registry_bytes)
    engine.save_private(engine.JOURNAL, old_journal_bytes)
    if not engine.live_ok(old_registry) or not engine.healthy(engine.authorization()):
        save_phase("incident")
        raise RuntimeError("baseline not healthy after repair rollback")
    save_phase("restored")
    return "original_incident_state_restored"


def recover():
    fd = engine.locked()
    try:
        return restore_from_archive(allowed_phases=("prepared",))
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--apply", action="store_true")
    options.add_argument("--recover", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run as openclaw, not root")
    try:
        if not args.apply and not args.recover:
            plan()
            print("BOB QUEUE UPDATE REPAIR: READY (read-only)")
            print("Preserved incident archive: tx-" + FIRST_RELEASE)
            print("production_modified: NO")
            return 0
        if args.confirm != (RECOVERY_APPROVAL if args.recover else APPROVAL):
            raise ValueError("explicit operator confirmation required")
        outcome = recover() if args.recover else repair()
        print("BOB QUEUE UPDATE REPAIR:", outcome)
        return 0 if outcome in (
            "baseline_reconciled_updater_patched",
            "original_incident_state_restored") else 1
    except (OSError, ValueError, RuntimeError, KeyError, TypeError,
            json.JSONDecodeError) as exc:
        print("BOB QUEUE UPDATE REPAIR: REFUSED (" + type(exc).__name__ + ")")
        print("Do not delete transaction journals or retry blindly.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
