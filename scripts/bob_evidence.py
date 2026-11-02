#!/usr/bin/env python3
"""Bob host evidence bundle: ONE read-only command instead of many pastes.

Run as the normal ``openclaw`` user inside OpenClawLab, from the trusted
checkout (no install / release needed):

    python3 ~/bob-next/scripts/bob_evidence.py            # last 24h
    python3 ~/bob-next/scripts/bob_evidence.py --since "2026-11-02 09:00"
    python3 ~/bob-next/scripts/bob_evidence.py --json

Guarantees (enforced by tests/test_bob_evidence.py):
- Never writes to SQLite (opened ``mode=ro`` via URI), never starts, stops,
  enables, resets or reloads any unit, never contacts Moltbook / OpenClaw /
  Ollama beyond a TCP connect, never reads credentials or persona files.
- Journal lines are ALLOW-LISTED: only systemd lifecycle lines and the
  workers' own structured status JSON (fixed keys, token-shaped values) are
  kept. Everything else (model text, feed text, tracebacks) is counted as
  ``omitted`` and never printed.
- A final secret scan refuses to emit anything that looks like a key/token.
- The only file written is ``~/.local/state/bob-evidence/latest.md`` (0600).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import ssl
import subprocess
import sys
from http.client import HTTPSConnection
from typing import Callable, Iterable

FORMAT = "bob-evidence-v1"

# Every unit Bob's topology knows about. Unknown units are simply reported as
# not-found by systemd; nothing is ever started.
UNITS = (
    "bob-moltbook-scout.timer", "bob-moltbook-scout.service",
    "bob-moltbook-publisher.timer", "bob-moltbook-publisher.service",
    "bob-r3-propose.timer", "bob-r3-propose.service",
    "bob-r4-propose.timer", "bob-r4-propose.service",
    "bob-v08-shadow.timer", "bob-v08-shadow.service",
    "bob-activity-manager.service", "openclaw-gateway.service",
    "bob-startup-reconcile.timer",
)
JOURNAL_UNITS = (
    "bob-r4-propose.service", "bob-r3-propose.service",
    "bob-moltbook-scout.service", "bob-moltbook-publisher.service",
    "bob-activity-manager.service",
)
SHOW_PROPS = (
    "LoadState", "ActiveState", "SubState", "Result", "UnitFileState",
    "LastTriggerUSec", "NextElapseUSecRealtime", "ExecMainStartTimestamp",
    "ExecMainExitTimestamp", "ExecMainStatus", "DropInPaths", "NRestarts",
)

# ---- allow-lists ---------------------------------------------------------
TOKEN = re.compile(r"[A-Za-z0-9_.:+\-]{0,96}\Z")
STATUS_KEYS = frozenset((
    "status", "reason", "source_run", "queued", "attempted",
    "dispatch_authorized", "phase", "release", "format",
))
LIFECYCLE = re.compile(
    r"(Starting|Started|Finished|Stopping|Stopped|Deactivated successfully"
    r"|Failed with result '[a-z-]+'|Main process exited, code=[a-z]+, "
    r"status=[0-9A-Z/]+|Consumed [0-9.a-z ]+ CPU time"
    r"|Scheduled restart job, restart counter is at [0-9]+)"
    r"[ .A-Za-z0-9_@/()\-:,']{0,160}\Z")
SECRET = re.compile(
    r"(moltbook_[A-Za-z0-9_]{8,}|sk-[A-Za-z0-9]{16,}|Bearer\s+[A-Za-z0-9._\-]{12,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|\"password\"\s*:|api[_-]?key\s*[=:])",
    re.IGNORECASE)
STATE_TABLES = (
    "publish_jobs", "r3_proposals", "r4_social_decisions", "r4_action_outbox",
    "r4_evidence_suggestions", "original_posts", "bob_memory_suggestions",
)
STATE_COLUMNS = ("state", "status")

Runner = Callable[[list, int], "tuple[int, str]"]


def default_runner(argv: list, timeout: int = 10) -> "tuple[int, str]":
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=timeout, errors="replace",
                           env={**os.environ, "SYSTEMD_PAGER": "",
                                "SYSTEMD_COLORS": "0", "LC_ALL": "C.UTF-8"})
        return p.returncode, (p.stdout or "")[:262144]
    except (OSError, subprocess.SubprocessError):
        return 127, ""


# ---- collectors ---------------------------------------------------------
def units(run: Runner) -> dict:
    out: dict = {}
    argv = ["systemctl", "--user", "show", "--no-pager"]
    for p in SHOW_PROPS:
        argv += ["-p", p]
    for unit in UNITS:
        code, text = run(argv + [unit], 10)
        props = {}
        for line in text.splitlines():
            key, _, value = line.partition("=")
            if key in SHOW_PROPS:
                props[key] = _safe_value(key, value)
        if props.get("LoadState") == "not-found":
            continue
        out[unit] = props if code == 0 else {"error": "systemctl_show_failed"}
    return out


def _safe_value(key: str, value: str) -> str:
    value = value.strip()[:200]
    if key == "DropInPaths":
        # Paths only, under the user's own systemd dir; report basenames.
        return " ".join(Path(x).parent.name + "/" + Path(x).name
                        for x in value.split() if x)
    if re.fullmatch(r"[A-Za-z0-9 :\-+./_]*", value):
        return value
    return "<unprintable>"


def timers(run: Runner) -> str:
    code, text = run(["systemctl", "--user", "list-timers", "--all",
                      "--no-pager"], 10)
    keep = [line.rstrip() for line in text.splitlines()
            if line.startswith("NEXT") or "bob-" in line or "openclaw" in line]
    return "\n".join(keep) if code == 0 else "list-timers failed"


def r4_schedule(run: Runner, home: Path) -> dict:
    tool = home / ".local/bin/bob-r4-schedule"
    if not tool.is_file():
        return {"error": "bob-r4-schedule not installed"}
    code, text = run([str(tool), "--status"], 30)
    try:
        data = json.loads(text.strip().splitlines()[-1]) if text.strip() else None
    except (ValueError, IndexError):
        data = None
    if not isinstance(data, dict):
        return {"error": "status_not_json", "exit": code}
    return {k: v for k, v in data.items()
            if isinstance(v, (bool, int, type(None))) or
            (isinstance(v, str) and TOKEN.fullmatch(v)) or
            (isinstance(v, list) and all(isinstance(x, str) and TOKEN.fullmatch(x) for x in v))}


def journal(run: Runner, unit: str, since: str, limit: int = 400) -> dict:
    code, text = run(["journalctl", "--user", "-u", unit, "--since", since,
                      "--no-pager", "-o", "json", "-n", str(limit)], 20)
    kept, omitted = [], 0
    for raw in text.splitlines():
        try:
            entry = json.loads(raw)
            msg = entry.get("MESSAGE")
            if isinstance(msg, list):  # binary messages arrive as byte lists
                omitted += 1
                continue
            ts = datetime.fromtimestamp(int(entry["__REALTIME_TIMESTAMP"]) / 1e6,
                                        tz=timezone.utc).astimezone()
        except (ValueError, KeyError, TypeError, OverflowError):
            omitted += 1
            continue
        line = classify(str(msg))
        if line is None:
            omitted += 1
        else:
            kept.append(ts.strftime("%m-%d %H:%M:%S ") + line)
    return {"lines": kept[-60:], "omitted": omitted,
            "error": None if code == 0 else "journalctl_failed"}


def classify(message: str):
    """Return a safe rendering of ``message`` or None to omit it."""
    message = message.strip()
    if message.startswith("{") and len(message) <= 2048:
        try:
            data = json.loads(message)
        except ValueError:
            return None
        if (isinstance(data, dict) and data and set(data) <= STATUS_KEYS and
                all(isinstance(v, bool) or (isinstance(v, str) and TOKEN.fullmatch(v))
                    for v in data.values())):
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return None
    if message.startswith("BOB ") and re.fullmatch(r"BOB [A-Z0-9 ]{2,40}: [a-z0-9_]{1,60}", message):
        return message
    if LIFECYCLE.fullmatch(message):
        return message
    return None


def installed(home: Path) -> dict:
    state = home / ".local/state/bob-updater"
    bindir = home / ".local/bin"
    result: dict = {}
    try:
        info = json.loads((state / "installed.json").read_text(encoding="utf-8"))
        result["release"] = str(info.get("release"))[:80]
        files = info.get("files") or {}
        ok, bad, missing = 0, [], []
        for name, digest in sorted(files.items()):
            p = bindir / name
            if not p.is_file():
                missing.append(name)
            elif hashlib.sha256(p.read_bytes()).hexdigest() == digest:
                ok += 1
            else:
                bad.append(name)
        result.update(files_ok=ok, files_mismatch=bad, files_missing=missing)
    except (OSError, ValueError, AttributeError) as exc:
        result["error"] = "registry_unreadable:" + type(exc).__name__
    try:
        tx = json.loads((state / "transaction.json").read_text(encoding="utf-8"))
        result["transaction"] = {k: tx.get(k) for k in ("release", "phase")}
    except (OSError, ValueError, AttributeError):
        result["transaction"] = None
    return result


def database(home: Path) -> dict:
    path = home / ".config/moltbook/activity-queue.sqlite3"
    if not path.is_file():
        return {"error": "database_missing"}
    out: dict = {"size_kb": path.stat().st_size // 1024}
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=3)
        try:
            db.execute("PRAGMA query_only=ON")
            tables = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            for table in STATE_TABLES:
                if table not in tables:
                    continue
                cols = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                col = next((c for c in STATE_COLUMNS if c in cols), None)
                if col is None:
                    out[table] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    continue
                out[table] = {
                    (str(k) if TOKEN.fullmatch(str(k)) else "<other>"): n
                    for k, n in db.execute(
                        f"SELECT {col},COUNT(*) FROM {table} GROUP BY {col}")}
        finally:
            db.close()
    except sqlite3.Error as exc:
        out["error"] = "sqlite:" + type(exc).__name__
    return out


def network(home: Path) -> dict:
    def port(p: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", p), timeout=1.5):
                return True
        except OSError:
            return False
    out = {"gateway_18789_listening": port(18789),
           "ollama_11434_listening": port(11434),
           "manager_18790_listening": port(18790)}
    ca = home / ".config/bob-system/manager-tls/ca.crt"
    if out["manager_18790_listening"] and ca.is_file():
        try:
            ctx = ssl.create_default_context(cafile=str(ca))
            conn = HTTPSConnection("127.0.0.1", 18790, timeout=3, context=ctx)
            conn.request("GET", "/healthz", headers={"Host": "127.0.0.1:18790"})
            res = conn.getresponse()
            out["manager_healthz_https"] = res.status
            conn.close()
        except (OSError, ssl.SSLError, ValueError) as exc:
            out["manager_healthz_https"] = "error:" + type(exc).__name__
    return out


def checkout(run: Runner, home: Path) -> dict:
    repo = home / "bob-next"
    if not (repo / ".git").exists():
        return {"error": "no ~/bob-next checkout"}
    out = {}
    for key, argv in (("branch", ["rev-parse", "--abbrev-ref", "HEAD"]),
                      ("head", ["rev-parse", "--short=12", "HEAD"]),
                      ("dirty_files", ["status", "--porcelain"])):
        code, text = run(["git", "-C", str(repo)] + argv, 10)
        out[key] = (len(text.splitlines()) if key == "dirty_files" else text.strip()[:60]) if code == 0 else None
    return out


def host(run: Runner) -> dict:
    code, text = run(["df", "-Pk", str(Path.home())], 5)
    free = None
    try:
        free = int(text.splitlines()[1].split()[3]) // 1024
    except (IndexError, ValueError):
        pass
    return {"user": os.environ.get("USER") or str(os.geteuid()),
            "hostname": socket.gethostname()[:64],
            "now_local": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "disk_free_mb": free}


# ---- assembly -----------------------------------------------------------
def collect(run: Runner = default_runner, home: Path | None = None,
            since: str = "24 hours ago") -> dict:
    home = Path.home() if home is None else Path(home)
    return {
        "format": FORMAT,
        "host": host(run),
        "checkout": checkout(run, home),
        "installed": installed(home),
        "r4_schedule": r4_schedule(run, home),
        "units": units(run),
        "timers": timers(run),
        "network": network(home),
        "database": database(home),
        "journal_since": since,
        "journal": {u: journal(run, u, since) for u in JOURNAL_UNITS},
    }


def render(data: dict) -> str:
    j = lambda x: json.dumps(x, indent=1, sort_keys=True, default=str)
    parts = [f"# Bob evidence · {data['host']['now_local']} · {data['host']['hostname']}",
             "", "Read-only sanitized bundle (`" + FORMAT + "`). Paste or attach as-is.", ""]
    for key in ("host", "checkout", "installed", "r4_schedule", "network", "database"):
        parts += [f"## {key}", "```json", j(data[key]), "```", ""]
    parts += ["## units", "```json", j(data["units"]), "```", "",
              "## timers", "```text", data["timers"], "```", "",
              f"## journal (since {data['journal_since']})"]
    for unit, info in data["journal"].items():
        parts += [f"### {unit}  (kept {len(info['lines'])}, omitted {info['omitted']})",
                  "```text", "\n".join(info["lines"]) or "(no allow-listed lines)", "```"]
    return "\n".join(parts) + "\n"


def secret_free(text: str) -> bool:
    return SECRET.search(text) is None


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", default="24 hours ago",
                    help='journalctl --since value (default "24 hours ago")')
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--no-save", action="store_true", help="do not write latest.md")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if os.geteuid() == 0:
        print("refusing: run as the normal openclaw user, not root", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[0-9A-Za-z :\-]{1,40}", args.since):
        print("refusing: --since must be a plain date/time or 'N hours ago'", file=sys.stderr)
        return 2
    data = collect(since=args.since)
    text = json.dumps(data, indent=1, sort_keys=True, default=str) if args.json else render(data)
    if not secret_free(text):
        print("refusing: output matched a secret pattern; nothing printed or saved",
              file=sys.stderr)
        return 3
    if not args.no_save:
        out = Path.home() / ".local/state/bob-evidence"
        out.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = out / ("latest.json" if args.json else "latest.md")
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
