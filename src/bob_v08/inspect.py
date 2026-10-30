"""Read-only R2 Now/Inbox presentation. No routes or authentication server.

An authenticated Activity Manager may call these renderers after the v0.8
package is deployed. Never serve them on an unauthenticated HTTP listener.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
import json
import sqlite3
import subprocess
import re

from .shadow import EVENT_DB, LEGACY
from .digest import build_digest

COLUMNS = ("at", "source_run", "post_id", "kind", "state", "reason", "action_type")
CSS = """<style>
.v8{display:grid;gap:12px;max-width:1100px;margin:auto;font:inherit}
.v8 *{box-sizing:border-box}.v8 section{border:1px solid #3b5778;background:#11243a;
border-radius:12px;padding:clamp(12px,2.2vw,19px);min-width:0}
.v8 h2{font-size:1.03rem;margin:0 0 10px}.v8 p,.v8 td,.v8 th{overflow-wrap:anywhere}
.v8 .quiet{font-size:.82rem;color:#b7cde5;line-height:1.55}
.v8 table{border-collapse:collapse;width:100%;font-size:.79rem;table-layout:fixed}
.v8 td,.v8 th{text-align:left;vertical-align:top;border-bottom:1px solid #345474;
padding:8px 5px}.v8 code{font-size:.76rem;overflow-wrap:anywhere}
.v8 .two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:700px){.v8 .two{grid-template-columns:1fr}
.v8 table{display:block;overflow-x:auto;white-space:normal}.v8 td{min-width:110px}}
@media(max-width:380px){.v8 section{padding:11px}.v8 td,.v8 th{font-size:.7rem}}
</style>"""


def timer_observation():
    """Report only actual systemd metadata; never infer a scheduled tick."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", "bob-v08-shadow.timer",
             "-p", "ActiveState", "-p", "NextElapseUSecRealtime", "--no-pager"],
            capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"state": "unknown", "next": ""}
    if result.returncode != 0 or len(result.stdout) > 1024:
        return {"state": "unknown", "next": ""}
    props = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            props[key] = value
    state = props.get("ActiveState", "unknown")
    if state not in ("active", "inactive", "failed", "activating", "deactivating"):
        state = "unknown"
    upcoming = props.get("NextElapseUSecRealtime", "")
    if (not isinstance(upcoming, str) or len(upcoming) > 100
            or not re.fullmatch(r"[A-Za-z0-9 :+.,/_-]*", upcoming)
            or upcoming in ("n/a", "n/a (no next)", "0")):
        upcoming = ""
    return {"state": state, "next": upcoming}


def read_status(path: Path = EVENT_DB, *, limit: int = 18, timer=None):
    """Read-only projection; opening this view must not create a database."""
    timer = timer if timer is not None else timer_observation()
    if type(limit) is not int or not 1 <= limit <= 40:
        raise ValueError("invalid_status_limit")
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        return {"state": "not_started", "events": [], "count": 0,
                "scheduled": timer["state"] == "active", "timer": timer}
    try:
        db = sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True,
                             timeout=2)
        try:
            db.execute("PRAGMA query_only=ON")
            rows = db.execute(
                "SELECT at,source_run,post_id,kind,state,reason,action_type "
                "FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        finally:
            db.close()
    except (sqlite3.Error, OSError):
        return {"state": "unavailable", "events": [], "count": 0,
                "scheduled": timer["state"] == "active", "timer": timer}
    events = [dict(zip(COLUMNS, row)) for row in rows]
    return {"state": "shadow_read_only" if events else "no_shadow_events",
            "events": events, "count": count,
            "scheduled": timer["state"] == "active", "timer": timer}


def now_content(status):
    if not isinstance(status, dict):
        raise ValueError("invalid_status")
    events = status.get("events", [])
    if not isinstance(events, list):
        raise ValueError("invalid_status")
    rows = []
    for event in events[:18]:
        if not isinstance(event, dict):
            continue
        rows.append("<tr><td>" + escape(str(event.get("at", ""))) +
                    "</td><td><code>" + escape(str(event.get("source_run", ""))) +
                    "</code></td><td>" + escape(str(event.get("kind", ""))) +
                    " / " + escape(str(event.get("action_type", ""))) +
                    "</td><td>" + escape(str(event.get("reason", ""))) + "</td></tr>")
    table = ("<table><thead><tr><th>UTC</th><th>Source run</th><th>Event/action</th>"
             "<th>Reason</th></tr></thead><tbody>" + "".join(rows) +
             "</tbody></table>") if rows else "<p>No verified shadow activity recorded yet.</p>"
    return (CSS + '<div class="v8"><section><h2>Bob v0.8 · Shadow Now</h2>'
            '<p class="quiet">This view reads the isolated v0.8 event log only. '
            'It does not operate the existing v0.7 publisher or report live '
            'Moltbook availability. Every v0.8 external action is blocked '
            'during R2 regardless of the displayed hypothetical policy result.</p>'
            '<div class="two"><p><b>State:</b> ' + escape(str(status.get("state", "unknown"))) +
            '</p><p><b>Recorded events:</b> ' +
            escape(str(status.get("count", 0))) + '</p></div>'
            '<p class="quiet"><b>Shadow timer:</b> ' +
            escape(str((status.get("timer") or {}).get("state", "unknown"))) +
            ' · <b>Next reported run:</b> ' +
            escape(str((status.get("timer") or {}).get("next") or "not reported")) +
            '</p></section>'
            '<section><h2>Recent evidence-linked decisions</h2>' + table +
            '</section></div>')


def inbox_content(status, digest):
    events = status.get("events", []) if isinstance(status, dict) else []
    anomalies = [e for e in events if isinstance(e, dict) and
                 e.get("kind") == "agent_error"][:8]
    items = ["<li><code>" + escape(str(e.get("source_run", ""))) + "</code> · " +
             escape(str(e.get("reason", ""))) + "</li>" for e in anomalies]
    problems = ("<ul>" + "".join(items) + "</ul>") if items else (
        "<p>No recent shadow model validation failures in the displayed window.</p>")
    observed = digest.get("observations", []) if isinstance(digest, dict) else []
    return (CSS + '<div class="v8"><section><h2>Shadow Inbox · informational only</h2>'
            '<p class="quiet">R2 has no actionable social proposals or autonomous '
            'publishing authority. The production v0.7 queues remain on their '
            'existing dashboard. This page is a preview, not an approval Inbox.</p>'
            '</section><section><h2>Recent issues</h2>' + problems +
            '</section><section><h2>Experience snapshot</h2>'
            '<p class="quiet">Source-verified saved Scout selections in this '
            'bounded read-only digest: ' + escape(str(len(observed))) +
            '. Publication is not independently rechecked public visibility.</p>'
            '</section></div>')


def render_now(wrap, *, path: Path = EVENT_DB):
    """The passed wrapper MUST be the already authenticated Activity Manager."""
    return wrap("Bob · Shadow Now", now_content(read_status(path)), "/v08/now")


def render_inbox(wrap, *, path: Path = EVENT_DB, source: Path = LEGACY):
    return wrap("Bob · Shadow Inbox",
                inbox_content(read_status(path),
                              build_digest(source, source / "activity-queue.sqlite3")),
                "/v08/inbox")
