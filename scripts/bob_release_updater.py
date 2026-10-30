#!/usr/bin/env python3
"""Bob's reusable, explicitly approved GitHub release updater.

"bobctl update" checks GitHub and asks for an exact typed approval only when a
new reviewed release manifest exists. "--check" only checks. "--recover"
restores a known incomplete update. No worker, publisher or API writes.
"""
from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
from http.client import HTTPConnection
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import time

HOME = Path.home()
BIN = HOME / ".local/bin"
CONFIG = HOME / ".config/bob-system/updater.json"
STATE_DIR = HOME / ".local/state/bob-updater"
REGISTRY = STATE_DIR / "installed.json"
JOURNAL = STATE_DIR / "transaction.json"
LOCK = STATE_DIR / "lock"
DB = HOME / ".config/moltbook/activity-queue.sqlite3"
BACKUP_DIR = HOME / ".local/state/bob-baseline/backups"
FORMAT = "bob-updater-v1"
FORMAT_V2 = "bob-updater-v2"  # R1: only the established, flat-file manifest shape.
BRANCH = "main"
CHANNELS = frozenset(("main", "next"))
REPO = "merberg-ai/bob-openclaw-moltbook"
RELEASE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{2,79}\Z")
TARGET = re.compile(r"(?:bobctl|bob[-_][a-zA-Z0-9._-]+|navigation_shell\.py)\Z")
MANIFEST = "releases/current.json"
ORIGINS = frozenset((
    "https://github.com/" + REPO + ".git",
    "https://github.com/" + REPO,
    "git@github.com:" + REPO + ".git",
))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_private(path: Path, *, directory=False):
    if path.is_symlink():
        raise ValueError("symlink private path")
    info = path.stat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("private path owner/type mismatch")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("unprivate file/directory permissions")


def private_dir(path: Path):
    if path.is_symlink():
        raise ValueError("symlink private directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    safe_private(path, directory=True)


def save_private(path: Path, data: bytes):
    if path.is_symlink():
        raise ValueError("symlink private destination")
    fd, tempname = tempfile.mkstemp(prefix=".bob-next-", dir=path.parent)
    temp = Path(tempname)
    try:
        with os.fdopen(fd, "wb") as out:
            os.fchmod(out.fileno(), 0o600)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path: Path):
    safe_private(path)
    if path.stat().st_size > 32768:
        raise ValueError("oversized private configuration")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid configuration object")
    return data


def shell(argv, *, timeout=45):
    result = subprocess.run(argv, text=True, capture_output=True, timeout=timeout,
                            check=False)
    if result.returncode:
        raise ValueError("operation refused: " + argv[0] + " " + (argv[1] if len(argv) > 1 else ""))
    return result.stdout.strip()


def read_checkout_config():
    """The old two-key configuration remains the default main channel."""
    conf = read_json(CONFIG)
    if (set(conf) not in ({"format", "checkout"}, {"format", "checkout", "channel"})
            or conf.get("format") != FORMAT
            or not isinstance(conf.get("checkout"), str)):
        raise ValueError("unexpected updater config")
    channel = conf.get("channel", BRANCH)
    if not isinstance(channel, str) or channel not in CHANNELS:
        raise ValueError("untrusted release channel")
    return conf, channel


def checkout_from_config():
    conf, channel = read_checkout_config()
    folder = Path(conf["checkout"])
    if not folder.is_absolute() or folder.is_symlink() or not folder.is_dir():
        raise ValueError("untrusted checkout")
    if folder.resolve() != folder:
        raise ValueError("checkout path is not canonical")
    if shell(["git", "-C", str(folder), "rev-parse", "--show-toplevel"]) != str(folder):
        raise ValueError("wrong Git checkout root")
    if shell(["git", "-C", str(folder), "branch", "--show-current"]) != channel:
        raise ValueError("unexpected release branch")
    if shell(["git", "-C", str(folder), "remote", "get-url", "origin"]) not in ORIGINS:
        raise ValueError("unexpected Git remote")
    if shell(["git", "-C", str(folder), "status", "--porcelain"]):
        raise ValueError("development checkout has uncommitted changes")
    return folder


def sync_checkout(folder):
    # Updating the development checkout NEVER installs anything by itself.
    _, channel = read_checkout_config()
    shell(["git", "-C", str(folder), "pull", "--ff-only", "origin", channel],
          timeout=75)
    if shell(["git", "-C", str(folder), "branch", "--show-current"]) != channel:
        raise ValueError("release branch changed during pull")
    if shell(["git", "-C", str(folder), "status", "--porcelain"]):
        raise ValueError("checkout modified after pull")


def switch_channel(folder, target):
    """Switch a trusted clean checkout; never install code or touch services.

    The config is committed last, after checkout and fast-forward verification.
    On an ordinary failure, restore the previous branch and exact config bytes.
    """
    if not isinstance(target, str) or target not in CHANNELS:
        raise ValueError("unsupported release channel")
    fd = locked()
    old_data = None
    original = None
    changed_config = False
    try:
        if checkout_from_config() != folder:
            raise ValueError("checkout changed before channel selection")
        conf, original = read_checkout_config()
        journal = read_journal()
        if journal and journal["phase"] not in ("complete", "rolled_back"):
            raise ValueError("incomplete update blocks channel selection")
        current = registry()
        if not live_ok(current):
            raise ValueError("installed file hash drift blocks channel selection")
        if target == original:
            return "unchanged"
        old_data = CONFIG.read_bytes()
        # Only allowlisted branch names and a previously verified origin.
        shell(["git", "-C", str(folder), "fetch", "--no-tags", "origin",
               "refs/heads/" + target + ":refs/remotes/origin/" + target], timeout=75)
        probe = subprocess.run(
            ["git", "-C", str(folder), "show-ref", "--verify", "--quiet",
             "refs/heads/" + target],
            capture_output=True, text=True, timeout=15, check=False)
        if probe.returncode not in (0, 1):
            raise ValueError("cannot inspect target branch")
        if probe.returncode == 0:
            shell(["git", "-C", str(folder), "switch", target])
            shell(["git", "-C", str(folder), "merge", "--ff-only",
                   "refs/remotes/origin/" + target], timeout=45)
        else:
            shell(["git", "-C", str(folder), "switch", "--track", "-c", target,
                   "refs/remotes/origin/" + target])
        if (shell(["git", "-C", str(folder), "branch", "--show-current"]) != target
                or shell(["git", "-C", str(folder), "status", "--porcelain"])):
            raise ValueError("target checkout verification failed")
        updated = dict(conf)
        updated["channel"] = target
        save_private(CONFIG, (json.dumps(updated, sort_keys=True) + "\n").encode())
        changed_config = True
        if checkout_from_config() != folder:
            raise ValueError("saved release channel verification failed")
        return "switched"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        # Failure before commit must not strand the trusted checkout on another
        # branch with the old channel. Never silently rewrite a divergent tree.
        try:
            if changed_config and old_data is not None:
                save_private(CONFIG, old_data)
            if original in CHANNELS and shell(
                    ["git", "-C", str(folder), "branch", "--show-current"]) != original:
                shell(["git", "-C", str(folder), "switch", original])
                if shell(["git", "-C", str(folder), "status", "--porcelain"]):
                    raise RuntimeError("channel rollback left a dirty checkout")
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            raise RuntimeError("channel switch needs manual recovery; no install attempted") from None
        raise
    finally:
        os.close(fd)

def locked():
    private_dir(STATE_DIR)
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
        os.close(fd)
        raise ValueError("unsafe updater lock")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def registry():
    info = read_json(REGISTRY)
    if (set(info) != {"format", "release", "files"} or info["format"] != FORMAT
            or not RELEASE_ID.fullmatch(info["release"])
            or not isinstance(info["files"], dict)):
        raise ValueError("invalid installed release registry")
    for name, sha in info["files"].items():
        if not TARGET.fullmatch(name) or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("invalid tracked file hash")
    return info


def manifest(folder):
    path = folder / MANIFEST
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("invalid release manifest")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict)
            or set(data) != {"format", "release", "from", "notes", "files", "restart_manager"}
            or data["format"] not in (FORMAT, FORMAT_V2) or not RELEASE_ID.fullmatch(data["release"])
            or not RELEASE_ID.fullmatch(data["from"])
            or not isinstance(data["notes"], str) or len(data["notes"]) > 800
            or type(data["restart_manager"]) is not bool
            or not isinstance(data["files"], list) or len(data["files"]) > 30):
        raise ValueError("unsupported release manifest")
    seen = set()
    for item in data["files"]:
        if not isinstance(item, dict) or set(item) not in ({"name", "source"}, {"name", "builder", "index"}):
            raise ValueError("unsupported release file entry")
        name = item.get("name")
        if not isinstance(name, str) or not TARGET.fullmatch(name) or name in seen:
            raise ValueError("unsafe or duplicate release destination")
        seen.add(name)
        if "source" in item:
            source = item["source"]
            if not isinstance(source, str):
                raise ValueError("unsafe source path")
            parts = PurePosixPath(source).parts
            if (len(parts) < 3 or parts[:2] not in (("src", "bin"), ("src", "lib"))) and source != "scripts/bob_release_updater.py":
                raise ValueError("source must be a reviewed src path or the updater itself")
        else:
            builder = item["builder"]
            if (not isinstance(builder, str) or not re.fullmatch(r"scripts/build_[a-zA-Z0-9_]+\.py", builder)
                    or item["index"] not in (0, 1) or type(item["index"]) is not int):
                raise ValueError("unsupported builder output")
    return data


def checked_source(folder, value):
    rel = PurePosixPath(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("unsafe source path")
    dest = folder
    for part in rel.parts:
        dest = dest / part
        if dest.is_symlink():
            raise ValueError("source symlink")
    if not dest.is_file() or dest.stat().st_size > 524288:
        raise ValueError("unsafe source file")
    return dest


def release_bytes(folder, item):
    if "source" in item:
        data = checked_source(folder, item["source"]).read_bytes()
    else:
        source = checked_source(folder, item["builder"])
        # Explicitly reviewed Git-tracked build script, invoked only for
        # a release declared in the GitHub manifest.
        sys.path.insert(0, str(folder / "scripts"))
        try:
            spec = importlib.util.spec_from_file_location("bob_release_builder", source)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            output = mod.build()
            if not isinstance(output, tuple) or len(output) != 2:
                raise ValueError("unexpected builder return")
            data = output[item["index"]]
        finally:
            sys.path.remove(str(folder / "scripts"))
    if not isinstance(data, bytes) or not 0 < len(data) <= 524288:
        raise ValueError("release content missing or oversized")
    if item["name"].endswith(".py") or item["name"].startswith("bob-"):
        compile(data, item["name"], "exec")
    return data


def live_ok(data):
    for name, sha in data["files"].items():
        target = BIN / name
        if target.is_symlink() or not target.is_file():
            return False
        st = target.stat()
        if st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o022:
            return False
        if digest(target.read_bytes()) != sha:
            return False
    return True


def authorization():
    creds = read_json(HOME / ".config/bob-system/lan-auth.json")
    if not isinstance(creds.get("username"), str) or not isinstance(creds.get("password"), str):
        raise ValueError("invalid private dashboard authentication")
    raw = (creds["username"] + ":" + creds["password"]).encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def healthy(auth):
    for route in ("/healthz", "/settings", "/activity", "/system/status", "/api/system/status"):
        conn = HTTPConnection("127.0.0.1", 18790, timeout=16 if "status" in route else 5)
        try:
            conn.request("GET", route, headers={"Host":"127.0.0.1:18790", "Authorization": auth})
            res = conn.getresponse()
            payload = res.read(262145)
            if res.status != 200 or len(payload) > 262144:
                return False
            if route == "/healthz" and json.loads(payload).get("ok") is not True:
                return False
            if route == "/api/system/status" and not isinstance(json.loads(payload).get("services"), list):
                return False
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        finally:
            conn.close()
    return True



def wait_for_health(auth, *, seconds=35):
    """Give a freshly restarted dashboard a bounded readiness window.

    A brief connection refusal after systemctl restart isn't a failed release.
    This performs authenticated GETs only; it never invokes worker endpoints.
    """
    deadline = time.monotonic() + seconds
    while True:
        if healthy(auth):
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(1.0, remaining))


def restart_manager():
    shell(["systemctl", "--user", "restart", "bob-activity-manager.service"], timeout=25)


def store_journal(data):
    save_private(JOURNAL, (json.dumps(data, sort_keys=True) + "\n").encode("utf-8"))


def read_journal():
    if not JOURNAL.exists():
        return None
    data = read_json(JOURNAL)
    if (data.get("format") != FORMAT or data.get("phase") not in
            ("prepared", "installed", "restarted", "rolled_back", "complete", "incident")
            or not RELEASE_ID.fullmatch(data.get("release", ""))):
        raise ValueError("unrecognized updater journal")
    return data


def write_target(name, data):
    path = BIN / name
    if path.is_symlink():
        raise ValueError("unsafe target symlink")
    fd, tempname = tempfile.mkstemp(prefix=".bob-code-", dir=BIN)
    temp = Path(tempname)
    try:
        with os.fdopen(fd, "wb") as out:
            os.fchmod(out.fileno(), 0o600 if name.endswith(".py") else 0o700)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
        fd = os.open(BIN, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temp.unlink(missing_ok=True)


def rollback(journal, *, auth):
    tx = STATE_DIR / ("tx-" + journal["release"])
    safe_private(tx, directory=True)
    original = json.loads((tx / "original.json").read_text(encoding="utf-8"))
    candidate = json.loads((tx / "candidate.json").read_text(encoding="utf-8"))
    old_registry = read_json(tx / "registry-before.json")
    if not isinstance(original, dict) or not isinstance(candidate, dict) or set(original) != set(candidate):
        raise ValueError("unexpected rollback archive")
    for name, sha in original.items():
        if not TARGET.fullmatch(name) or not isinstance(sha, str):
            raise ValueError("unsafe rollback reference")
        path = BIN / name
        oldfile = tx / ("old-" + name)
        if (not isinstance(candidate[name], str) or not re.fullmatch(r"[0-9a-f]{64}", candidate[name])
                or (path.exists() and (path.is_symlink() or digest(path.read_bytes()) not in
                                      (candidate[name], sha)))):
            raise ValueError("installed target changed outside transaction")
        if sha == "absent":
            if path.is_symlink():
                raise ValueError("cannot remove unexpected symlink")
            if path.exists():
                path.unlink()
        else:
            safe_private(oldfile)
            old = oldfile.read_bytes()
            if digest(old) != sha:
                raise ValueError("original file archive changed")
            write_target(name, old)
    save_private(REGISTRY, (json.dumps(old_registry, sort_keys=True) + "\n").encode("utf-8"))
    if journal["restart_manager"]:
        restart_manager()
    if not live_ok(old_registry) or not wait_for_health(auth):
        store_journal({**journal, "phase": "incident"})
        raise RuntimeError("rollback HTTP health failed")
    store_journal({**journal, "phase": "rolled_back"})
    return "baseline_restored"


def update(folder, current, plan, contents, *, auth):
    private_dir(STATE_DIR)
    fd = locked()
    try:
        if read_journal() and read_journal()["phase"] not in ("complete", "rolled_back"):
            raise ValueError("incomplete prior release; use --recover")
        if not live_ok(current):
            raise ValueError("installed file hash drift")
        if not healthy(auth):
            raise ValueError("existing authenticated UI unhealthy")
        # Backup is verified before any live code is replaced.
        from backup_live_sqlite import create_verified_backup
        create_verified_backup(DB, BACKUP_DIR)
        tx = STATE_DIR / ("tx-" + plan["release"])
        if tx.exists() or tx.is_symlink():
            raise ValueError("release journal archive exists")
        private_dir(tx)
        originals = {}
        for name in contents:
            installed = BIN / name
            if installed.is_symlink():
                raise ValueError("unsafe installed target")
            if installed.exists():
                if not installed.is_file() or installed.stat().st_uid != os.getuid():
                    raise ValueError("unexpected installed file")
                data = installed.read_bytes()
                originals[name] = digest(data)
                save_private(tx / ("old-" + name), data)
            else:
                originals[name] = "absent"
        save_private(tx / "original.json", json.dumps(originals,sort_keys=True).encode())
        save_private(tx / "candidate.json", json.dumps(
            {name: digest(blob) for name, blob in contents.items()}, sort_keys=True).encode())
        save_private(tx / "registry-before.json", json.dumps(current, sort_keys=True).encode())
        journal = {"format": FORMAT, "release": plan["release"],
                   "phase": "prepared", "restart_manager": plan["restart_manager"]}
        store_journal(journal)
        try:
            step = "installing listed files"
            for name, payload in contents.items():
                if name not in current["files"] and (BIN / name).exists():
                    raise ValueError("unmanaged destination exists")
                write_target(name, payload)
            store_journal({**journal, "phase": "installed"})
            if plan["restart_manager"]:
                step = "restarting Activity Manager"
                restart_manager()
            store_journal({**journal, "phase": "restarted"})
            step = "checking file hashes and authenticated dashboard"
            next_files = dict(current["files"])
            next_files.update({name: digest(blob) for name, blob in contents.items()})
            next_state = {"format": FORMAT, "release": plan["release"], "files": next_files}
            if not live_ok(next_state):
                raise RuntimeError("updated installation file hash mismatch")
            if not wait_for_health(auth):
                raise RuntimeError("dashboard failed bounded post-restart health checks")
            save_private(REGISTRY, json.dumps(next_state, sort_keys=True).encode())
            store_journal({**journal, "phase": "complete"})
            return "updated"
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            # Safe stage only, never print HTTP responses, credentials or payloads.
            print("BOB UPDATE: failed at " + step + " (" + type(exc).__name__ + ")")
            try:
                rollback(journal, auth=auth)
            except (OSError, ValueError, RuntimeError):
                store_journal({**journal, "phase": "incident"})
                raise RuntimeError("rollback incident; inspection required") from None
            return "rolled_back"
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--recover", action="store_true")
    group.add_argument("--channel", choices=sorted(CHANNELS))
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run as openclaw (not root)")
    try:
        folder = checkout_from_config()
        sys.path.insert(0, str(folder / "scripts"))
        if args.channel is not None:
            if not sys.stdin.isatty() or input(
                    "Type SWITCH-" + args.channel.upper() + " to change the source channel (NO INSTALL): "
            ) != "SWITCH-" + args.channel.upper():
                raise ValueError("channel change approval not granted")
            result = switch_channel(folder, args.channel)
            print("BOB UPDATE: channel " + args.channel + " (" + result + "); no production changes")
            return 0
        if args.recover:
            journal = read_journal()
            if not journal or journal["phase"] not in ("prepared", "installed", "restarted"):
                raise ValueError("no recoverable interrupted transaction")
            print("Recovery requested for:", journal["release"])
            if not sys.stdin.isatty() or input("Type RECOVER to restore original code: ") != "RECOVER":
                raise ValueError("recovery approval not granted")
            print("BOB UPDATE:", rollback(journal, auth=authorization()))
            return 0
        sync_checkout(folder)
        current = registry()
        plan = manifest(folder)
        if plan["release"] == current["release"]:
            if not live_ok(current):
                raise ValueError("installed files differ from recorded release")
            print("BOB UPDATE: up to date (" + current["release"] + ")")
            return 0
        if plan["from"] != current["release"]:
            raise ValueError("release chain mismatch; no automatic skipping")
        if not plan["files"]:
            raise ValueError("empty release is not an upgrade")
        contents = {item["name"]: release_bytes(folder, item) for item in plan["files"]}
        if not live_ok(current):
            raise ValueError("installed files drifted; no overwrite")
        print("BOB UPDATE AVAILABLE:", plan["release"])
        print("Release:", plan["notes"])
        print("Files:", ", ".join(contents))
        print("Restart Activity Manager:", plan["restart_manager"])
        if args.check:
            print("BOB UPDATE: CHECK ONLY; no production changes")
            return 0
        if not sys.stdin.isatty() or input("Type UPDATE to back up and install this release: ") != "UPDATE":
            print("BOB UPDATE: no production changes")
            return 1
        outcome = update(folder, current, plan, contents, auth=authorization())
        print("BOB UPDATE:", outcome)
        return 0 if outcome == "updated" else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError, ImportError, AttributeError) as exc:
        print("BOB UPDATE: REFUSED (" + type(exc).__name__ + ")")
        print("No automatic retry. Review updater journal for an incomplete transaction.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
