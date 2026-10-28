#!/usr/bin/env python3
"""Generate and exercise an INERT v0.7.0 service graph in a disposable sandbox.

Never installs, enables, starts or restarts systemd units. No network, Bob
source, Moltbook API, Ollama, live database, credentials or Windows startup.
Unit names are unique, contents are synthetic, all output stays in an
automatically removed TemporaryDirectory. This is NOT an installer.
"""
from __future__ import annotations
from contextlib import closing
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile

from stage_mock_actor import MARKER, ROLES, validate

PREFIX = "bob-v070-stage-"
RUNNING = {"gateway", "manager"}
ONE_SHOT = {"scout", "publisher", "original-worker", "reconcile"}
ORDER = ("gateway", "manager", "scout", "publisher", "original-worker", "reconcile")
TIMERS = {
    "scout": ("OnUnitActiveSec=1h", "AccuracySec=1min"),
    "publisher": ("OnBootSec=2min", "OnUnitActiveSec=1min", "AccuracySec=15s"),
    "original-worker": ("OnBootSec=3min", "OnUnitActiveSec=2min", "AccuracySec=20s"),
    "reconcile": ("OnStartupSec=30s", "OnUnitInactiveSec=2min", "AccuracySec=15s"),
}
MOCK_SOURCE = Path(__file__).resolve().with_name("stage_mock_actor.py")
NO_PRODUCTION_NAMES = ("bob-moltbook-", "bob-original-worker.", "bob-activity-manager.",
                       "openclaw-gateway.", "bob-startup-reconcile.")


def check_root(root: Path) -> None:
    if (not root.is_absolute() or not root.name.startswith(PREFIX)
            or root.is_symlink() or root == Path.home()
            or not root.is_dir() or any(root.iterdir())):
        raise ValueError("Refusing nonempty or non-staging sandbox")
    if stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise ValueError("Sandbox is not private")


def save_private(path: Path, content: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(content)


def make_release(root: Path, label: str, fixture: bytes) -> None:
    if label not in {"baseline", "candidate"}:
        raise ValueError("Invalid mock release")
    bindir = root / "releases" / label / "bin"
    bindir.mkdir(parents=True, mode=0o700)
    save_private(bindir / "stage_mock_actor.py", fixture)
    (bindir / "stage_mock_actor.py").chmod(0o700)
    save_private(bindir.parent / "FIXTURE-SHA256", hashlib.sha256(fixture).hexdigest().encode())


def point_to(root: Path, label: str) -> None:
    if label not in {"baseline", "candidate"}:
        raise ValueError("Invalid release target")
    dest = root / "releases" / label / "bin" / "stage_mock_actor.py"
    if dest.is_symlink() or not dest.is_file():
        raise ValueError("Missing release fixture")
    ref = root / "current"
    if ref.exists() and not ref.is_symlink():
        raise ValueError("Refusing unexpected release pointer")
    new = root / ".stage-pointer-new"
    if new.exists() or new.is_symlink():
        raise ValueError("Stale stage pointer")
    try:
        new.symlink_to("releases/" + label, target_is_directory=True)
        os.replace(new, ref)
    finally:
        if new.is_symlink():
            new.unlink()


def write_service(root: Path, role: str) -> str:
    if role not in ROLES:
        raise ValueError("Unknown role")
    name = PREFIX + role + ".service"
    actor = root / "current/bin/stage_mock_actor.py"
    command = (f"{sys.executable} {actor} --stage-root {root} "
               f"--role {role} --{'serve' if role in RUNNING else 'once'}")
    # The stage path is created internally under tempfile. Refuse special
    # characters before rendering systemd directives with embedded paths.
    if not re.fullmatch(r"[/A-Za-z0-9_.-]+", str(root)):
        raise ValueError("Unexpected sandbox path characters")
    lines = [
        "# INERT STAGING ONLY - NEVER INSTALL OR ENABLE",
        "[Unit]",
        "Description=Bob v0.7.0 synthetic " + role,
        "ConditionPathExists=" + str(root / "STAGING-MARKER.json"),
    ]
    if role == "scout":
        lines.extend(["After=" + PREFIX + "gateway.service",
                      "Wants=" + PREFIX + "gateway.service"])
    lines.extend([
        "[Service]",
        "Type=" + ("simple" if role in RUNNING else "oneshot"),
        "ExecStart=" + command,
        "WorkingDirectory=" + str(root),
        "Environment=BOB_STAGE_ONLY=1",
        "NoNewPrivileges=yes",
        # Stage fixture lives in /tmp. Avoid PrivateTmp for this intentionally
        # ephemeral graph, even if corresponding production units use it.
        "PrivateTmp=no",
    ])
    if role in RUNNING:
        lines.extend([
            "Restart=" + ("always" if role == "gateway" else "on-failure"),
            "RestartSec=5s",
            "[Install]",
            "WantedBy=default.target",
        ])
    return "\n".join(lines) + "\n"


def write_timer(role: str) -> str:
    if role not in TIMERS:
        raise ValueError("No mock timer for role")
    lines = [
        "# INERT STAGING ONLY - NEVER INSTALL OR ENABLE",
        "[Unit]",
        "Description=Bob v0.7.0 synthetic " + role + " timer",
        "[Timer]",
        "Unit=" + PREFIX + role + ".service",
        *TIMERS[role],
        "[Install]",
        "WantedBy=timers.target",
    ]
    return "\n".join(lines) + "\n"


def create(root: Path, source: Path = MOCK_SOURCE) -> dict:
    check_root(root)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Unsafe mock actor source")
    fixture = source.read_bytes()
    if len(fixture) > 32_000 or not fixture.startswith(b"#!/usr/bin/env python3\n"):
        raise ValueError("Unexpected mock actor")
    # The only executable content is our explicitly named inert fixture.
    save_private(root / "STAGING-MARKER.json",
                 json.dumps({"purpose": MARKER, "production_allowed": False}).encode())
    (root / "private").mkdir(mode=0o700)
    dbpath = root / "private" / "synthetic.sqlite3"
    old_umask = os.umask(0o077)
    try:
        with closing(sqlite3.connect(dbpath)) as db:
            db.execute("CREATE TABLE simulated_events (id INTEGER PRIMARY KEY, role TEXT NOT NULL, release_tag TEXT NOT NULL)")
            db.commit()
    finally:
        os.umask(old_umask)
    dbpath.chmod(0o600)
    for name in ("baseline", "candidate"):
        make_release(root, name, fixture)
    point_to(root, "baseline")
    (root / "units").mkdir(mode=0o700)
    names = []
    for role in ORDER:
        name = PREFIX + role + ".service"
        save_private(root / "units" / name, write_service(root, role).encode())
        names.append(name)
    for role in TIMERS:
        name = PREFIX + role + ".timer"
        save_private(root / "units" / name, write_timer(role).encode())
        names.append(name)
    manifest = {
        "purpose": MARKER,
        "deployable": False,
        "service_count": len(ORDER),
        "timer_count": len(TIMERS),
        "system_legacy_scout_included": False,
        "fixture_sha256": hashlib.sha256(fixture).hexdigest(),
        "units_sha256": {name: hashlib.sha256((root / "units" / name).read_bytes()).hexdigest()
                         for name in sorted(names)},
        "notes": [
            "Synthetic timer cadences are modeled on sanitized v0.7.0 review metadata",
            "No real systemd installation, live service commands, or external API access",
            "Production PrivateTmp settings are intentionally not replicated in /tmp sandbox",
            "Actual ExecStart, environment, drop-in precedence and Gateway directives remain unverified",
        ],
    }
    save_private(root / "STAGING-GRAPH.json", json.dumps(manifest, sort_keys=True).encode())
    verify(root)
    return manifest


def verify(root: Path) -> None:
    marker = json.loads((root / "STAGING-GRAPH.json").read_text())
    if marker.get("purpose") != MARKER or marker.get("deployable") is not False:
        raise ValueError("Not a staging-only graph")
    expected = {PREFIX + role + ".service" for role in ORDER} | {
        PREFIX + role + ".timer" for role in TIMERS
    }
    actual = {p.name for p in (root / "units").iterdir()}
    if actual != expected or set(marker["units_sha256"]) != expected:
        raise ValueError("Staged unit membership mismatch")
    for name in expected:
        file = root / "units" / name
        if file.is_symlink() or not file.is_file():
            raise ValueError("Symlink or missing unit")
        raw = file.read_bytes()
        if hashlib.sha256(raw).hexdigest() != marker["units_sha256"][name]:
            raise ValueError("Staging unit content drift")
        text = raw.decode("utf-8")
        if (not text.startswith("# INERT STAGING ONLY - NEVER INSTALL OR ENABLE\n")
                or any(x in text for x in NO_PRODUCTION_NAMES)
                or text.count("[Unit]\n") != 1):
            raise ValueError("Invalid staging-only service graph")
        if name.endswith(".service"):
            if (text.count("ExecStart=") != 1 or "STAGING-MARKER.json" not in text
                    or f"--stage-root {root} " not in text
                    or "Environment=BOB_STAGE_ONLY=1\n" not in text):
                raise ValueError("Unsafe service fixture")
        else:
            role = name[len(PREFIX):-len(".timer")]
            if "Unit=" + PREFIX + role + ".service\n" not in text:
                raise ValueError("Timer does not reference staging unit")
    # The staged release pointer is checked by the inert actor.
    validate(root)


def run_fixture(root: Path, role: str) -> str:
    if role not in ROLES:
        raise ValueError("Unrecognized mock role")
    actor = root / "current/bin/stage_mock_actor.py"
    if actor.is_symlink():
        raise ValueError("Symlink actor refused")
    process = subprocess.run(
        [sys.executable, str(actor), "--stage-root", str(root),
         "--role", role, "--once"],
        capture_output=True, text=True, timeout=8, check=False,
        env={"PATH":"/usr/bin:/bin", "HOME":str(root), "PYTHONDONTWRITEBYTECODE":"1"},
    )
    if process.returncode:
        raise RuntimeError("Inert stage actor failed")
    return process.stdout.strip()


def rehearsal(root: Path) -> dict:
    verify(root)
    # Actors are run as isolated child Python processes, not by systemd.
    for role in ORDER:
        run_fixture(root, role)
    point_to(root, "candidate")
    for role in ORDER:
        run_fixture(root, role)
    # Simulated bad health gate: switch only the mock code pointer back.
    candidate_health_ok = False
    if not candidate_health_ok:
        point_to(root, "baseline")
    for role in ("gateway", "manager"):
        run_fixture(root, role)
    verify(root)
    with closing(sqlite3.connect(root / "private/synthetic.sqlite3")) as db:
        entries = db.execute("SELECT role,release_tag FROM simulated_events ORDER BY id").fetchall()
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    if (integrity != "ok" or len(entries) != 14
            or [v for _, v in entries[:6]] != ["baseline"]*6
            or [v for _, v in entries[6:12]] != ["candidate"]*6
            or [v for _, v in entries[12:]] != ["baseline"]*2
            or os.readlink(root / "current") != "releases/baseline"):
        raise AssertionError("Synthetic service/rollback acceptance failed")
    return {
        "services": 6, "timers": 4, "mock_runs": len(entries),
        "independent_sqlite": True, "health_failure_rollback": True,
        "post_swap_writes_preserved": True, "live_install_modified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as unprivileged OpenClawLab user")
    try:
        with tempfile.TemporaryDirectory(prefix=PREFIX) as temp:
            root = Path(temp)
            create(root)
            result = rehearsal(root)
    except (OSError, ValueError, RuntimeError, AssertionError, KeyError,
            sqlite3.Error, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print("INERT STAGING GRAPH: REFUSED", type(exc).__name__,
              "(live installation untouched)", file=sys.stderr)
        return 1
    print("INERT STAGING SERVICE GRAPH: PASS")
    for key, value in result.items():
        print(" ", key + ":", value)
    print("No installed systemd units, live code/SQLite, credentials, Windows startup or APIs touched.")
    print("All temporary staging files removed. NOT DEPLOYABLE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
