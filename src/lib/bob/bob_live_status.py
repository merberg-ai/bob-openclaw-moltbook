"""Bounded read-only Bob dependency status snapshot, no secrets or mutations."""
from __future__ import annotations
import json
import socket
import subprocess
import urllib.request

UNITS = (
    ("Gateway", "openclaw-gateway.service"),
    ("Scout", "bob-moltbook-scout.service"),
    ("Scout timer", "bob-moltbook-scout.timer"),
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
        return "running" if result.returncode == 0 and state == "active" else (
            "inactive" if state in ("inactive", "failed", "deactivating") else "unknown")
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
        return "ready" if isinstance(payload, dict) and isinstance(payload.get("models"), list) else "unknown"
    except (OSError, ValueError, TimeoutError):
        return "unavailable"

def gateway_port():
    try:
        with socket.create_connection(("127.0.0.1", 18789), timeout=0.7):
            return "listening"
    except OSError:
        return "unavailable"

def snapshot():
    items = [{"name": label, "state": unit_state(unit)} for label, unit in UNITS]
    items.append({"name": "Gateway port", "state": gateway_port()})
    items.append({"name": "Ollama", "state": ollama_state()})
    return {"services": items, "note": "Running indicates a process, not end-to-end readiness. Jobs are not inferred from service state."}
