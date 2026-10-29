#!/usr/bin/env python3
"""One-time guarded installation of "bobctl update".

Default mode inspects only. --apply explicitly installs one new updater file,
changes bobctl's command dispatch, and registers the exact live v0.7.2 code.
Neither the Activity Manager nor the scout/publisher services are restarted.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import bob_release_updater as engine
import build_v072_publication_truth_candidate as builder
from backup_live_sqlite import create_verified_backup

ROOT = Path(__file__).resolve().parents[1]
BIN = Path.home() / ".local/bin"
OLD_BOBCTL = ROOT / "release_baselines/v072-updater/bobctl"
NEW_BOBCTL = ROOT / "src/bin/bobctl"
UPDATER_SOURCE = ROOT / "scripts/bob_release_updater.py"
APPROVE = "INSTALL-BOB-UPDATER"

# Files already installed and verified by the successful v0.7.2 release series.
# None is replaced by this bootstrap. Exact hash drift stops the installation.
TRACKED = {
    "bob_dashboard_auth.py": "src/lib/bob/bob_dashboard_auth.py",
    "bob_live_status.py": "src/lib/bob/bob_live_status.py",
    "bob_status_view.py": "src/lib/bob/bob_status_view.py",
    "bob_job_tracking.py": "src/lib/bob/bob_job_tracking.py",
    "bob-moltbook-scout": "src/bin/bob-moltbook-scout",
    "bob-moltbook-publisher": "src/bin/bob-moltbook-publisher",
    "bob-original-worker": "src/bin/bob-original-worker",
}


def source(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 524288:
        raise ValueError("unsafe bootstrap source")
    blob = path.read_bytes()
    compile(blob, str(path), "exec")
    return blob


def snapshot():
    old_ctl, new_ctl, updater = (source(x) for x in
                                 (OLD_BOBCTL, NEW_BOBCTL, UPDATER_SOURCE))
    if old_ctl == new_ctl:
        raise ValueError("bobctl update entrypoint missing")
    # Confirm only the reviewed update hook and help lines changed.
    baseline = old_ctl.decode("utf-8")
    candidate = new_ctl.decode("utf-8")
    marker = '    if len(args) > 1:\n        help_text()\n        return 2'
    handler = """    if name == "update":
        if len(args) > 2 or (len(args) == 2 and args[1] not in ("--check", "--recover")):
            help_text()
            return 2
        updater = BIN / "bob-release-updater"
        if updater.is_symlink() or not updater.is_file():
            print("Updater not installed; run the one-time bootstrap from GitHub.", file=sys.stderr)
            return 1
        return subprocess.run([sys.executable, str(updater), *args[1:]], check=False).returncode
"""
    for line in (
        "  update          Check GitHub release and optionally apply verified update\n",
        "  update --check  Read-only release check (may fast-forward the development checkout)\n",
        "  update --recover Restore interrupted code update from sealed journal\n",
    ):
        if candidate.count(line) != 1:
            raise ValueError("unexpected bobctl help change")
        candidate = candidate.replace(line, "", 1)
    if candidate.count(handler + marker) != 1:
        raise ValueError("unexpected bobctl command change")
    candidate = candidate.replace(handler + marker, marker, 1)
    if candidate != baseline:
        raise ValueError("unrelated bobctl edits")
    manager, nav = builder.build()
    blobs = {"bob-activity-manager": manager,
             "navigation_shell.py": nav}
    for name, rel in TRACKED.items():
        blobs[name] = source(ROOT / rel)
    blobs["bobctl"] = old_ctl
    for name, original in blobs.items():
        target = BIN / name
        if target.is_symlink() or not target.is_file():
            raise ValueError("missing installed baseline: " + name)
        info = target.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            raise ValueError("unsafe live file: " + name)
        if engine.digest(target.read_bytes()) != engine.digest(original):
            raise ValueError("installed baseline differs from GitHub: " + name)
    if ((BIN / "bob-release-updater").exists()
            or (BIN / "bob-release-updater").is_symlink()
            or engine.CONFIG.exists() or engine.CONFIG.is_symlink()
            or engine.REGISTRY.exists() or engine.REGISTRY.is_symlink()
            or engine.JOURNAL.exists() or engine.JOURNAL.is_symlink()):
        raise ValueError("updater already installed or a prior transaction exists")
    if not engine.healthy(engine.authorization()):
        raise ValueError("current dashboard not healthy")
    blobs["bobctl"] = new_ctl
    blobs["bob-release-updater"] = updater
    return old_ctl, new_ctl, updater, {
        "format": engine.FORMAT,
        "release": "v0.7.2-updater-bootstrap",
        "files": {name: engine.digest(data) for name, data in blobs.items()},
    }


def install():
    # Exact live inspection before any side effects.
    old_ctl, new_ctl, updater, state = snapshot()
    engine.private_dir(engine.STATE_DIR)
    lock = engine.locked()
    try:
        # Double-check after exclusive lock.
        snapshot()
        # Reuse the proven online, restore-verified SQLite backup utility.
        create_verified_backup(engine.DB, engine.BACKUP_DIR)
        engine.save_private(engine.STATE_DIR / "bootstrap-bobctl-before", old_ctl)
        journal = {
            "format": engine.FORMAT, "release": state["release"],
            "phase": "prepared", "restart_manager": False,
        }
        engine.store_journal(journal)
        try:
            engine.write_target("bob-release-updater", updater)
            engine.private_dir(engine.CONFIG.parent)
            engine.save_private(engine.CONFIG, json.dumps({
                "format": engine.FORMAT,
                "checkout": str(ROOT.resolve()),
            },sort_keys=True).encode())
            engine.save_private(engine.REGISTRY, json.dumps(state, sort_keys=True).encode())
            engine.write_target("bobctl", new_ctl)
            engine.store_journal({**journal, "phase": "installed"})
            if (engine.digest((BIN / "bobctl").read_bytes()) != engine.digest(new_ctl)
                    or not engine.live_ok(state) or not engine.healthy(engine.authorization())):
                raise RuntimeError("bootstrap verification failed")
            # Updater is present but no application release is pending.
            if engine.manifest(ROOT)["release"] != state["release"]:
                raise ValueError("bootstrap manifest has an unexpected release")
            engine.store_journal({**journal, "phase": "complete"})
            return "installed"
        except (OSError, ValueError, RuntimeError):
            if (BIN / "bobctl").is_file() and engine.digest((BIN / "bobctl").read_bytes()) in (
                    engine.digest(old_ctl), engine.digest(new_ctl)):
                engine.write_target("bobctl", old_ctl)
            else:
                engine.store_journal({**journal, "phase": "incident"})
                raise RuntimeError("installed bobctl changed; manual recovery required")
            updated = BIN / "bob-release-updater"
            if updated.is_file() and engine.digest(updated.read_bytes()) == engine.digest(updater):
                updated.unlink()
            for path in (engine.CONFIG, engine.REGISTRY):
                if path.is_file():
                    path.unlink()
            engine.store_journal({**journal, "phase": "rolled_back"})
            return "rolled_back"
    finally:
        os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run as openclaw, not root")
    try:
        if not args.apply:
            snapshot()
            print("BOB UPDATER BOOTSTRAP: READY (read-only)")
            print("production_modified: NO")
            return 0
        if args.confirm != APPROVE:
            raise ValueError("explicit bootstrap confirmation required")
        outcome = install()
        print("BOB UPDATER BOOTSTRAP:", outcome)
        if outcome == "installed":
            print("Run: bobctl update")
        return 0 if outcome == "installed" else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        print("BOB UPDATER BOOTSTRAP: REFUSED (" + type(exc).__name__ + ")")
        print("No automatic retry. Inspect ~/.local/state/bob-updater/transaction.json if present.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
