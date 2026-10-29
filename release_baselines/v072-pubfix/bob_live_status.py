"""Bounded read-only Bob dependency status snapshot, no secrets or mutations."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from bob_job_tracking import read_checkpoints
from pathlib import Path
import sqlite3
import socket
import subprocess
import urllib.request

UNITS = (
    ("Gateway", "openclaw-gateway.service"),
    ("Scout", "bob-moltbook-scout.service"),
    ("Scout timer", "bob-moltbook-scout.timer"),
    ("Publisher", "bob-moltbook-publisher.service"),
    ("Publisher timer", "bob-moltbook-publisher.timer"),
    ("Activity Manager", "bob-activity-manager.service"),
)
def unit_state(name):
    if name not in {unit for _, unit in UNITS}:
        raise ValueError("unknown service")
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", name],
            capture_output=True, text=True, timeout=1.5, check=False)
        state = result.stdout.strip()
        if result.returncode == 0 and state == "active":
            return "running"
        if state == "failed":
            return "failed"
        if state == "inactive" and name.endswith(".service") and name in {
                "bob-moltbook-scout.service", "bob-moltbook-publisher.service"}:
            return "idle"  # periodic one-shot jobs normally exit between executions
        return "inactive" if state in ("inactive", "deactivating") else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"

def ollama_state():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5) as resp:
            if resp.status != 200:
                return "unavailable"
            content = resp.read(65537)
        if len(content) > 65536:
            return "unknown"
        payload = json.loads(content)
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            return "unknown"
        model_names = {name for m in payload["models"] if isinstance(m, dict)
                       for name in [m.get("name") or m.get("model")] if isinstance(name, str)}
        return "ready" if "qwen3.5:9b" in model_names else "model_missing"
    except (OSError, ValueError, TimeoutError):
        return "unavailable"

def gateway_port():
    try:
        with socket.create_connection(("127.0.0.1", 18789), timeout=0.7):
            return "listening"
    except OSError:
        return "unavailable"

def queue_snapshot(path=None):
    """Read bounded observed queue states; never change schema or job state."""
    database = Path(path) if path is not None else Path.home() / ".config/moltbook/activity-queue.sqlite3"
    if database.is_symlink() or not database.is_file():
        return {"available": False, "jobs": []}
    try:
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=1) as db:
            db.execute("PRAGMA query_only=ON")
            comments = db.execute(
                "SELECT 'comment', run_id, state, created_at, updated_at, "
                "CASE WHEN last_error IS NOT NULL AND last_error != '' THEN 1 ELSE 0 END "
                "FROM publish_jobs ORDER BY created_at DESC LIMIT 20").fetchall()
            originals = db.execute(
                "SELECT 'original', id, state, created_at, updated_at, "
                "CASE WHEN last_error IS NOT NULL AND last_error != '' THEN 1 ELSE 0 END "
                "FROM original_posts ORDER BY created_at DESC LIMIT 20").fetchall()
            requests = db.execute(
                "SELECT 'generation', id, state, created_at, "
                "COALESCE(completed_at, created_at), "
                "CASE WHEN error IS NOT NULL AND error != '' THEN 1 ELSE 0 END "
                "FROM original_requests ORDER BY created_at DESC LIMIT 20").fetchall()
        jobs = [
            {"kind": kind, "job_id": ident if isinstance(ident, str) else "",
             "state": state if isinstance(state, str) else "unknown",
             "created": created if isinstance(created, str) else "",
             "updated": updated if isinstance(updated, str) else "",
             "has_error": bool(has_error),
             "automatic_retry": False}
            for kind, ident, state, created, updated, has_error in
            (comments + originals + requests)
        ]
        jobs.sort(key=lambda item: item["created"], reverse=True)
        return {"available": True, "jobs": jobs[:30]}
    except (sqlite3.Error, OSError, ValueError):
        return {"available": False, "jobs": []}


def snapshot():
    items = [{"name": label, "state": unit_state(unit)} for label, unit in UNITS]
    items.append({"name": "Gateway port", "state": gateway_port()})
    items.append({"name": "Ollama", "state": ollama_state()})
    return {"services": items, "queue": queue_snapshot(),
            "workers": read_checkpoints(),
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "note": "Running indicates a process, not end-to-end readiness. Queue states are recorded values, not inferred progress."}
