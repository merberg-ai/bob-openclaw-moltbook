"""Explicit, reversible R2 shadow activation of a versioned Python archive.

The existing v0.7 updater first installs the reviewed flat bootstrap files.
Only this separately approved command copies the archive into a versioned
directory and registers ONE user timer for read-only shadow decisions.
Never publishes, installs root/system units, edits legacy DB or reads API keys.
"""
from __future__ import annotations

from pathlib import Path
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile

HOME = Path.home()
RELEASE = "v0.8.0-shadow1"
BUNDLE_NAME = "bob_v08_package.pyz"
BIN = HOME / ".local/bin"
UPDATER_LOCK = HOME / ".local/state/bob-updater/lock"
REGISTRY = HOME / ".local/state/bob-updater/installed.json"
STATE = HOME / ".local/state/bob-v08-activation"
JOURNAL = STATE / "journal.json"
LOCK = STATE / "lock"
STORE = HOME / ".local/share/bob"
RELEASE_DIR = STORE / "releases" / RELEASE
ARCHIVE = RELEASE_DIR / BUNDLE_NAME
POINTER = STORE / "current.json"
UNITS = HOME / ".config/systemd/user"
SERVICE = "bob-v08-shadow.service"
TIMER = "bob-v08-shadow.timer"
SHA = re.compile(r"[0-9a-f]{64}\Z")
PHASES = ("prepared", "files_ready", "active", "deactivating", "inactive", "incident")


def units():
    service = (
        "[Unit]\nDescription=Bob v0.8 shadow decision (NO Moltbook writes)\n"
        "After=network-online.target\n"
        "[Service]\nType=oneshot\n"
        "ExecStart=%h/.local/bin/bob-v08-shadow --once\n"
        "NoNewPrivileges=true\nPrivateTmp=true\n"
        "TimeoutStartSec=330\n")
    timer = (
        "[Unit]\nDescription=Bob v0.8 periodic shadow observations\n"
        "[Timer]\nOnActiveSec=2min\nOnUnitInactiveSec=20min\n"
        "RandomizedDelaySec=120s\nAccuracySec=1min\n"
        "Persistent=false\nUnit=bob-v08-shadow.service\n"
        "[Install]\nWantedBy=timers.target\n")
    return {SERVICE: service.encode(), TIMER: timer.encode()}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private_directory(path):
    if path.is_symlink():
        raise ValueError("unsafe_directory_symlink")
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not path.is_dir() or path.stat().st_uid != os.getuid() or (
            stat.S_IMODE(path.stat().st_mode) & 0o077):
        raise ValueError("unsafe_private_directory")


def regular_file(path, *, max_size=512 * 1024, private=False):
    if path.is_symlink() or not path.is_file():
        raise ValueError("unsafe_file")
    st = path.stat()
    if st.st_uid != os.getuid() or not 0 < st.st_size <= max_size:
        raise ValueError("unsafe_file_owner_or_size")
    if private and stat.S_IMODE(st.st_mode) & 0o077:
        raise ValueError("unsafe_private_file")
    return path.read_bytes()


def safe_write(path, raw):
    if path.exists() or path.is_symlink():
        raise ValueError("destination_already_exists")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".bob-v08-")
    try:
        with os.fdopen(fd, "wb") as out:
            os.fchmod(out.fileno(), 0o600)
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def save_phase(phase, bundle_sha):
    if phase not in PHASES or not SHA.fullmatch(bundle_sha):
        raise ValueError("invalid_activation_journal")
    payload = (json.dumps({"format": "bob-v08-activation-v1",
                           "release": RELEASE, "phase": phase,
                           "bundle_sha": bundle_sha}, sort_keys=True) + "\n").encode()
    # Journal updates, unlike first-create release files, must be atomic replace.
    fd, tmp = tempfile.mkstemp(dir=STATE, prefix=".bob-v08-journal-")
    try:
        with os.fdopen(fd, "wb") as out:
            os.fchmod(out.fileno(), 0o600)
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, JOURNAL)
    finally:
        Path(tmp).unlink(missing_ok=True)


def read_phase():
    if not JOURNAL.exists():
        return None
    obj = json.loads(regular_file(JOURNAL, max_size=4096, private=True))
    if (not isinstance(obj, dict)
            or set(obj) != {"format", "release", "phase", "bundle_sha"}
            or obj["format"] != "bob-v08-activation-v1"
            or obj["release"] != RELEASE or obj["phase"] not in PHASES
            or not isinstance(obj["bundle_sha"], str)
            or not SHA.fullmatch(obj["bundle_sha"])):
        raise ValueError("invalid_activation_journal")
    return obj


def reviewed_bundle():
    """Never trust an arbitrary zip path, release ID or registry value."""
    obj = json.loads(regular_file(REGISTRY, max_size=32768, private=True))
    if (not isinstance(obj, dict) or obj.get("format") != "bob-updater-v1"
            or obj.get("release") != RELEASE or not isinstance(obj.get("files"), dict)):
        raise ValueError("unexpected_installed_release")
    expected = obj["files"].get(BUNDLE_NAME)
    if not isinstance(expected, str) or not SHA.fullmatch(expected):
        raise ValueError("missing_reviewed_bundle_hash")
    data = regular_file(BIN / BUNDLE_NAME)
    if digest(data) != expected:
        raise ValueError("installed_bundle_hash_drift")
    if "bob-v08-shadow" not in obj["files"] or "bob-v08-activate" not in obj["files"]:
        raise ValueError("missing_reviewed_entrypoints")
    return data, expected


def systemctl(*args):
    result = subprocess.run(["systemctl", "--user", *args], capture_output=True,
                            text=True, timeout=35, check=False)
    if result.returncode:
        # Never echo journal data or untrusted stderr to the operator.
        raise RuntimeError("systemctl_shadow_transition_failed")


def lock(path):
    if path.is_symlink() or not path.parent.is_dir():
        raise ValueError("unsafe_lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or (
                stat.S_IMODE(info.st_mode) & 0o077):
            raise ValueError("unsafe_lock_file")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BaseException:
        os.close(fd)
        raise


def verified_unit_paths(bundle_sha):
    """Check ALL file contents before removing any service definitions."""
    for name, raw in units().items():
        path = UNITS / name
        if regular_file(path, max_size=8192) != raw:
            raise ValueError("shadow_service_file_modified")
    if (regular_file(ARCHIVE) != regular_file(BIN / BUNDLE_NAME)
            or digest(regular_file(ARCHIVE)) != bundle_sha):
        raise ValueError("versioned_shadow_archive_modified")
    pointer = json.loads(regular_file(POINTER, max_size=4096, private=True))
    if pointer != {"release": RELEASE, "sha256": bundle_sha}:
        raise ValueError("shadow_activation_pointer_modified")


def _cleanup(bundle_sha):
    """Only remove exact R2-owned files; refuse unrelated or changed paths."""
    if UNITS.is_symlink():
        raise ValueError("unsafe_systemd_directory")
    if UNITS.is_dir():
        for name, contents in units().items():
            path = UNITS / name
            if path.exists() or path.is_symlink():
                if regular_file(path, max_size=8192) != contents:
                    raise ValueError("shadow_service_file_modified")
    if POINTER.exists() or POINTER.is_symlink():
        data = json.loads(regular_file(POINTER, max_size=4096, private=True))
        if data != {"release": RELEASE, "sha256": bundle_sha}:
            raise ValueError("shadow_activation_pointer_modified")
    if ARCHIVE.exists() or ARCHIVE.is_symlink():
        if digest(regular_file(ARCHIVE)) != bundle_sha:
            raise ValueError("versioned_shadow_archive_modified")
    # Never remove units if systemd's stop/disable result is uncertain.
    # This may leave an incident for guarded operator recovery, but it cannot
    # silently strand an active timer without its matching unit definition.
    systemctl("disable", "--now", TIMER)
    systemctl("stop", SERVICE)
    for name in units():
        (UNITS / name).unlink(missing_ok=True)
    systemctl("daemon-reload")
    POINTER.unlink(missing_ok=True)
    ARCHIVE.unlink(missing_ok=True)
    if RELEASE_DIR.is_dir():
        RELEASE_DIR.rmdir()


def activate():
    private_directory(STATE)
    activator = lock(LOCK)
    updater = lock(UPDATER_LOCK)
    try:
        source, sha = reviewed_bundle()
        prior = read_phase()
        if prior is not None and prior["phase"] != "inactive":
            raise ValueError("activation_already_recorded")
        # Never overwrite another unit, version pointer or staged version.
        if (POINTER.exists() or POINTER.is_symlink() or RELEASE_DIR.exists()
                or RELEASE_DIR.is_symlink()
                or any((UNITS / name).exists() or (UNITS / name).is_symlink()
                       for name in units())):
            raise ValueError("activation_conflicts_with_existing_state")
        save_phase("prepared", sha)
        try:
            private_directory(STORE)
            private_directory(STORE / "releases")
            private_directory(RELEASE_DIR)
            if UNITS.is_symlink():
                raise ValueError("unsafe_systemd_directory")
            UNITS.mkdir(mode=0o700, parents=True, exist_ok=True)
            safe_write(ARCHIVE, source)
            if digest(regular_file(ARCHIVE)) != sha:
                raise ValueError("versioned_bundle_hash_mismatch")
            for name, raw in units().items():
                safe_write(UNITS / name, raw)
            safe_write(POINTER, (json.dumps({"release": RELEASE, "sha256": sha},
                                            sort_keys=True) + "\n").encode())
            save_phase("files_ready", sha)
            verified_unit_paths(sha)
            systemctl("daemon-reload")
            systemctl("enable", "--now", TIMER)
            systemctl("is-enabled", TIMER)
            systemctl("is-active", TIMER)
            save_phase("active", sha)
            return "active"
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            try:
                _cleanup(sha)
                save_phase("inactive", sha)
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
                save_phase("incident", sha)
                raise RuntimeError("shadow_activation_needs_recovery") from None
            return "rolled_back"
    finally:
        os.close(updater)
        os.close(activator)


def deactivate():
    private_directory(STATE)
    activator = lock(LOCK)
    updater = lock(UPDATER_LOCK)
    try:
        phase = read_phase()
        if phase is None or phase["phase"] not in ("active", "files_ready", "incident"):
            raise ValueError("no_active_shadow_install")
        sha = phase["bundle_sha"]
        # Fail closed when the external files drift; never delete them blindly.
        if phase["phase"] == "active":
            verified_unit_paths(sha)
        save_phase("deactivating", sha)
        _cleanup(sha)
        save_phase("inactive", sha)
        return "inactive"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        if (phase := read_phase()) and phase["phase"] == "deactivating":
            save_phase("incident", phase["bundle_sha"])
        raise
    finally:
        os.close(updater)
        os.close(activator)


def status():
    phase = read_phase() if JOURNAL.exists() else None
    return {
        "installed": phase["phase"] if phase else "not_activated",
        "release": RELEASE,
        "versioned_archive": ARCHIVE.is_file() and not ARCHIVE.is_symlink(),
        "user_timer_defined": (UNITS / TIMER).is_file() and
                              not (UNITS / TIMER).is_symlink(),
        "note": "shadow only; no publishing permissions"
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--activate", action="store_true")
    group.add_argument("--deactivate", action="store_true")
    group.add_argument("--recover", action="store_true")
    group.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if os.geteuid() == 0:
        parser.error("run as openclaw, never root")
    if args.status:
        try:
            print(json.dumps(status(), sort_keys=True))
            return 0
        except (OSError, ValueError, json.JSONDecodeError):
            print("BOB SHADOW: status unavailable; inspect private activation journal")
            return 1
    action = ("ACTIVATE-SHADOW" if args.activate else
              "RECOVER-SHADOW" if args.recover else "DEACTIVATE-SHADOW")
    if not __import__("sys").stdin.isatty() or input(
            "Type " + action + " to confirm the local shadow timer transition: ") != action:
        print("BOB SHADOW: no installation change")
        return 1
    try:
        result = activate() if args.activate else deactivate()
        print("BOB SHADOW:", result)
        return 0 if result in ("active", "inactive") else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError, BlockingIOError) as exc:
        print("BOB SHADOW: REFUSED (" + type(exc).__name__ + ")")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
