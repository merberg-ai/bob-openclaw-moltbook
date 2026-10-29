#!/usr/bin/env python3
"""Migrate the already-installed Bob updater from the feature checkout to main.

One-time operation, NOT a clean installer. Default is read-only; explicit
--apply is required. Leaves both working checkouts and all Bob services alone.
Only the installed updater, private updater config and private release registry
change. Previous bytes are sealed privately and can be recovered if interrupted.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys

import bob_release_updater as engine

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "release_baselines/v072-main-migration/bob_release_updater.py"
NEW = ROOT / "scripts/bob_release_updater.py"
OLD_RELEASE = "v0.7.2-updater-bootstrap"
NEW_RELEASE = "v0.7.2-main-channel"
OLD_BRANCH = "feature/v0.7.1-navigation"
STATE = Path.home() / ".local/state/bob-main-migration"
JOURNAL = STATE / "transaction.json"
APPROVE = "MIGRATE-BOB-UPDATER-TO-MAIN"
RECOVER = "RECOVER-BOB-UPDATER-MIGRATION"
FORMAT = "bob-main-migration-v1"
SNAPSHOT_NAMES = ("updater-before", "config-before", "registry-before")
PHASES = ("prepared", "applied", "complete", "restoring", "restored", "incident")


def inspected_source(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 524288:
        raise ValueError("unsafe release source")
    data = path.read_bytes()
    compile(data, str(path), "exec")
    return data


def assert_checkout(path, branch):
    if not path.is_absolute() or path.is_symlink() or not path.is_dir() or path.resolve() != path:
        raise ValueError("unexpected checkout path")
    if engine.shell(["git", "-C", str(path), "rev-parse", "--show-toplevel"]) != str(path):
        raise ValueError("not a Git checkout root")
    if engine.shell(["git", "-C", str(path), "branch", "--show-current"]) != branch:
        raise ValueError("checkout on wrong branch")
    if engine.shell(["git", "-C", str(path), "remote", "get-url", "origin"]) not in engine.ORIGINS:
        raise ValueError("unexpected Git origin")
    if engine.shell(["git", "-C", str(path), "status", "--porcelain"]):
        raise ValueError("checkout contains uncommitted changes")


def plan():
    if engine.BRANCH != "main":
        raise ValueError("new updater is not main-pinned")
    assert_checkout(ROOT, "main")
    old = inspected_source(OLD)
    new = inspected_source(NEW)
    original_branch = b'BRANCH = "feature/v0.7.1-navigation"'
    main_branch = b'BRANCH = "main"'
    if old.count(original_branch) != 1 or new != old.replace(original_branch, main_branch, 1):
        raise ValueError("updater migration includes unrelated modifications")
    old_conf = engine.read_json(engine.CONFIG)
    if set(old_conf) != {"format", "checkout"} or old_conf["format"] != engine.FORMAT:
        raise ValueError("installed updater config changed")
    previous_checkout = Path(old_conf["checkout"])
    assert_checkout(previous_checkout, OLD_BRANCH)
    old_state = engine.registry()
    if old_state["release"] != OLD_RELEASE or not engine.live_ok(old_state):
        raise ValueError("installed release or tracked file hashes differ")
    if old_state["files"].get("bob-release-updater") != engine.digest(old):
        raise ValueError("live updater does not match the reviewed pinned baseline")
    updater_path = engine.BIN / "bob-release-updater"
    if updater_path.is_symlink() or not updater_path.is_file() or updater_path.read_bytes() != old:
        raise ValueError("installed updater code differs from approved baseline")
    released = engine.manifest(ROOT)
    if (released["release"] != NEW_RELEASE or released["from"] != NEW_RELEASE
            or released["files"] or released["restart_manager"]):
        raise ValueError("main channel must start with a no-op manifest")
    if not engine.healthy(engine.authorization()):
        raise ValueError("authenticated Activity Manager is unhealthy")
    next_conf = {"format": engine.FORMAT, "checkout": str(ROOT)}
    next_state = {"format": engine.FORMAT, "release": NEW_RELEASE,
                  "files": dict(old_state["files"])}
    next_state["files"]["bob-release-updater"] = engine.digest(new)
    return {
        "old_updater": old,
        "new_updater": new,
        "old_conf_bytes": engine.CONFIG.read_bytes(),
        "old_registry_bytes": engine.REGISTRY.read_bytes(),
        "new_conf_bytes": json.dumps(next_conf, sort_keys=True).encode() + b"\n",
        "new_registry_bytes": json.dumps(next_state, sort_keys=True).encode() + b"\n",
        "new_registry": next_state,
        "old_checkout": str(previous_checkout),
    }


def write_journal(stage):
    if stage not in PHASES:
        raise ValueError("invalid migration phase")
    engine.save_private(JOURNAL, (json.dumps(
        {"format": FORMAT, "phase": stage}, sort_keys=True) + "\n").encode())


def read_journal():
    if not JOURNAL.exists():
        return None
    data = engine.read_json(JOURNAL)
    if set(data) != {"format", "phase"} or data["format"] != FORMAT or data["phase"] not in PHASES:
        raise ValueError("invalid migration journal")
    return data["phase"]


def snapshots():
    result = {}
    for name in SNAPSHOT_NAMES:
        f = STATE / name
        engine.safe_private(f)
        if f.stat().st_size > 524288:
            raise ValueError("oversized recovery snapshot")
        result[name] = f.read_bytes()
    return result


def restore(old_data, new_data):
    """Restore only code and config still matching the old/new known hashes."""
    backup = snapshots()
    if backup["updater-before"] != old_data:
        raise ValueError("sealed updater baseline differs")
    locations = (
        (engine.BIN / "bob-release-updater", backup["updater-before"], new_data),
        (engine.CONFIG, backup["config-before"], None),
        (engine.REGISTRY, backup["registry-before"], None),
    )
    # Validate all destinations before changing ANY of them.
    for file, old, new in locations:
        if file.is_symlink() or not file.is_file():
            raise ValueError("recovery destination missing or symlinked")
        if file == engine.CONFIG:
            expected_new = json.dumps(
                {"format": engine.FORMAT, "checkout": str(ROOT)}, sort_keys=True).encode() + b"\n"
        elif file == engine.REGISTRY:
            state = json.loads(old)
            state["release"] = NEW_RELEASE
            state["files"]["bob-release-updater"] = engine.digest(new_data)
            expected_new = json.dumps(state, sort_keys=True).encode() + b"\n"
        else:
            expected_new = new
        if file.read_bytes() not in (old, expected_new):
            raise ValueError("recovery destination was modified outside migration")
    write_journal("restoring")
    engine.write_target("bob-release-updater", backup["updater-before"])
    engine.save_private(engine.CONFIG, backup["config-before"])
    engine.save_private(engine.REGISTRY, backup["registry-before"])
    if (not engine.live_ok(json.loads(backup["registry-before"]))
            or engine.CONFIG.read_bytes() != backup["config-before"]
            or not engine.healthy(engine.authorization())):
        write_journal("incident")
        raise RuntimeError("original updater recovery health verification failed")
    write_journal("restored")
    return "baseline_restored"


def apply(*, recover=False):
    fd = engine.locked()
    try:
        engine.private_dir(STATE)
        # The updater's own lock also protects against concurrent bobctl update.
        phase = read_journal()
        old_data = inspected_source(OLD)
        new_data = inspected_source(NEW)
        if recover:
            if phase not in ("prepared", "applied", "restoring"):
                raise ValueError("no recoverable interrupted migration")
            return restore(old_data, new_data)
        if phase is not None:
            raise ValueError("migration already recorded; cannot overwrite it")
        change = plan()
        for name, raw in zip(SNAPSHOT_NAMES, (
                change["old_updater"], change["old_conf_bytes"], change["old_registry_bytes"])):
            f = STATE / name
            if f.exists() or f.is_symlink():
                raise ValueError("existing migration snapshot")
            engine.save_private(f, raw)
        write_journal("prepared")
        try:
            engine.write_target("bob-release-updater", change["new_updater"])
            engine.save_private(engine.REGISTRY, change["new_registry_bytes"])
            engine.save_private(engine.CONFIG, change["new_conf_bytes"])
            write_journal("applied")
            if (not engine.live_ok(change["new_registry"])
                    or engine.CONFIG.read_bytes() != change["new_conf_bytes"]
                    or engine.checkout_from_config() != ROOT
                    or not engine.healthy(engine.authorization())):
                raise RuntimeError("main release channel did not pass health checks")
            write_journal("complete")
            return "main_channel_installed"
        except (OSError, ValueError, RuntimeError):
            try:
                return "rolled_back_" + restore(change["old_updater"], change["new_updater"])
            except (OSError, ValueError, RuntimeError):
                write_journal("incident")
                raise RuntimeError("migration rollback incident; inspect private journal") from None
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--recover", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run as openclaw, never root")
    try:
        if not args.apply and not args.recover:
            change = plan()
            print("BOB MAIN MIGRATION: READY (read-only)")
            print("Current checkout:", change["old_checkout"])
            print("Target checkout:", ROOT)
            print("Services or database modified: NO")
            return 0
        if args.confirm != (RECOVER if args.recover else APPROVE):
            raise ValueError("explicit owner confirmation required")
        outcome = apply(recover=args.recover)
        print("BOB MAIN MIGRATION:", outcome)
        return 0 if outcome in ("main_channel_installed", "baseline_restored") else 1
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError,
            TypeError, KeyError, OverflowError) as exc:
        print("BOB MAIN MIGRATION: REFUSED (" + type(exc).__name__ + ")")
        print("If a migration started, inspect ~/.local/state/bob-main-migration/transaction.json.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
