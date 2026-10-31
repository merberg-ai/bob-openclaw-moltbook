#!/usr/bin/env python3
"""R3.0 preview: sanitized, read-only Bob cutover inventory. Never sends or installs.

No credential loading, journal scraping, raw queue text, identity files, arbitrary
unit names, or database mutations. This is a *design report*, not authority to
enable a new publisher. Running it does not stop or start any workers.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

HOME = Path.home()
QUEUE = HOME / ".config/moltbook/activity-queue.sqlite3"
PAUSED = HOME / ".config/bob-system/paused"

# Exact reviewed service names. No user-provided unit names or shell commands.
UNITS = (
    ("user", "bob-moltbook-scout.timer"),
    ("user", "bob-moltbook-publisher.timer"),
    ("user", "bob-moltbook-publisher.service"),
    ("user", "bob-moltbook-scout.service"),
    ("user", "bob-original-worker.timer"),
    ("user", "bob-original-worker.service"),
    ("user", "bob-startup-reconcile.timer"),
    ("user", "bob-startup-reconcile.service"),
    ("user", "bob-r3-candidate-publisher.timer"),
    ("user", "bob-r3-candidate-publisher.service"),
    ("user", "bob-v08-shadow.timer"),
    ("user", "bob-v08-shadow.service"),
    ("user", "bob-activity-manager.service"),
    ("user", "openclaw-gateway.service"),
    ("system", "bob-moltbook-scout.timer"),
    ("system", "bob-moltbook-scout.service"),
)
SAFE_LOAD = {"loaded", "not-found", "masked", "error", "bad-setting", "stub", "merged"}
SAFE_ACTIVE = {"active", "inactive", "activating", "deactivating", "failed", "reloading"}
SAFE_SUB = {"waiting", "running", "dead", "exited", "failed", "start", "stop", "auto-restart"}
SAFE_ENABLE = {"enabled", "disabled", "static", "indirect", "masked", "masked-runtime",
               "enabled-runtime", "generated", "transient", "linked", "linked-runtime"}
SAFE_RESULT = {"success", "exit-code", "signal", "core-dump", "timeout", "watchdog",
               "start-limit-hit", "resources", "protocol", "dependency", "condition"}
STATES = {"queued", "sending", "uncertain", "published", "failed",
          "verifying", "verified_unconfirmed", "awaiting_verification",
          "verification_expired", "needs_review", "expired", "cancelled"}
MODES = {"manual", "auto"}

def _label(value, allowed):
    return value if isinstance(value, str) and value in allowed else "unknown"

def unit_facts(scope, name, *, run=subprocess.run):
    if (scope, name) not in UNITS:
        raise ValueError("unrecognized_cutover_unit")
    command = ["systemctl", "--user" if scope == "user" else "--system",
               "show", name, "--no-pager",
               "--property=LoadState,ActiveState,SubState,UnitFileState,Result"]
    try:
        proc = run(command, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        proc = None
    values = {}
    if proc is not None and proc.returncode == 0 and len(proc.stdout) <= 1200:
        for line in proc.stdout.splitlines():
            key, eq, value = line.partition("=")
            if eq and key in ("LoadState", "ActiveState", "SubState", "UnitFileState", "Result"):
                values[key] = value.strip()
    return {
        "scope": scope, "unit": name,
        "load": _label(values.get("LoadState"), SAFE_LOAD),
        "active": _label(values.get("ActiveState"), SAFE_ACTIVE),
        "sub": _label(values.get("SubState"), SAFE_SUB),
        "enabled": _label(values.get("UnitFileState"), SAFE_ENABLE),
        "result": _label(values.get("Result"), SAFE_RESULT),
    }

def _marker_status(path):
    if path.is_symlink():
        return "unavailable"
    try:
        return "paused" if path.is_file() else "not_paused"
    except OSError:
        return "unavailable"

def queue_facts(path=QUEUE, *, paused=PAUSED):
    """Only derived state counts and validated policy values, from SQLite mode=ro."""
    safe = {"status": "unavailable", "mode_counts": {}, "attempts_with_timestamp": 0,
            "auto_enabled": "unknown", "pause": _marker_status(paused),
            "policy_limits": {}, "policy_status": "unavailable"}
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024 * 1024:
        return safe
    try:
        with sqlite3.connect(path.absolute().as_uri() + "?mode=ro",
                             uri=True, timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            grouped = db.execute(
                "SELECT mode,state,COUNT(*) FROM publish_jobs GROUP BY mode,state").fetchall()
            counts = Counter()
            for mode, state, count in grouped:
                key = _label(mode, MODES) + "/" + _label(state, STATES)
                counts[key] += int(count)
            attempts = db.execute(
                "SELECT COUNT(*) FROM publish_jobs WHERE attempted_at IS NOT NULL").fetchone()[0]
            setting = db.execute(
                "SELECT value FROM publish_settings WHERE name='auto_enabled'").fetchone()
            auto = "enabled" if setting and setting[0] == "1" else (
                "disabled" if setting is None or setting[0] == "0" else "invalid")
            # Same deployed validation module, not a second reimplementation of limits.
            root = str(Path(__file__).resolve().parents[1] / "src/lib/bob")
            if root not in sys.path:
                sys.path.insert(0, root)
            from bob_activity_limits import read_limits
            try:
                limits = read_limits(db)
                policy_status = "valid"
            except (ValueError, TypeError, sqlite3.Error):
                limits, policy_status = {}, "invalid"
            safe.update(status="ok", mode_counts=dict(sorted(counts.items())),
                        attempts_with_timestamp=int(attempts),
                        auto_enabled=auto, policy_limits=limits,
                        policy_status=policy_status)
    except (OSError, ValueError, sqlite3.Error):
        pass
    return safe

def inventory(*, queue_path=QUEUE, paused=PAUSED, get_unit=unit_facts):
    return {
        "format": "bob-r3-readonly-inventory-v1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "design_only_no_publishing_or_cutover",
        "cutover_authorized": False,
        "service_status": [get_unit(scope, name) for scope, name in UNITS],
        "legacy_queue": queue_facts(queue_path, paused=paused),
        "limitations": [
            "One-time read only snapshot; not a transaction spanning systemd and SQLite.",
            "Unit states show service status, not whether a POST or agent decision occurred.",
            "attempts_with_timestamp is historical, not a count of verified public comments.",
            "Any invalid/missing queue policy or service status blocks cutover readiness.",
            "Only the existing legacy publisher owns real Moltbook dispatch.",
            "No R3 cutover or new authority can be granted by this report.",
        ],
    }

def main():
    if hasattr(__import__("os"), "geteuid") and __import__("os").geteuid() == 0:
        print("R3 INVENTORY: refuse root")
        return 1
    data = inventory()
    print(json.dumps(data, sort_keys=True, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
