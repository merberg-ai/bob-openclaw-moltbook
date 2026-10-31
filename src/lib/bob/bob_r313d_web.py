"""Isolated additive Bob-R3 owner UI, designed as a mixin over existing Manager.

The hash-pinned old Activity Manager source and all legacy GET/POST handlers
stay byte-for-byte untouched. A separately generated versioned manager may
append this mixin as a subclass after the original Handler definition.

The same authenticated LAN Basic auth, exact Host, origin, CSRF and local
fixed SQLite boundary are required for every R3 state-changing operation.
No API key, Moltbook network client or publisher is imported here.
"""
from __future__ import annotations
from html import escape
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
import hmac
import re
import sqlite3

from bob_publish_common import DATA,connect as publish_conn


def esc(value):
    return escape(str(value if value is not None else ""), quote=True)


def tab_page(title,content):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(title)} | Bob Activity Manager</title><style>'
        'body{background:#0b1220;color:#e7eefb;font:16px/1.5 system-ui;'
        'max-width:1000px;margin:0 auto;padding:24px}'
        'a{color:#b3d4ff}nav{display:flex;gap:14px;flex-wrap:wrap}'
        'nav a{border:1px solid #31496b;border-radius:8px;padding:9px}'
        'article{margin:20px 0;background:#172239;border:1px solid #34435d;'
        'padding:18px;border-radius:12px}'
        'pre{white-space:pre-wrap;word-break:break-word;background:#0e1b30;'
        'padding:16px}form{margin:12px 0;display:inline-block}'
        'button{padding:10px;margin:5px;color:white;background:#246b58;'
        'border-radius:8px;border:1px solid #509d8c;cursor:pointer}'
        'button.danger{background:#703641}'
        'input{padding:9px;background:#101d32;border:1px solid #586b88;color:white}'
        '.meta{color:#aebed7;font-size:.87rem}</style></head><body>'
        '<header><h1>💀 Bob R3 Controls</h1><nav>'
        '<a href="/">Activity</a><a href="/v08/now">Shadow Now</a>'
        '<a href="/v08/inbox">Shadow Inbox</a></nav></header>'
        +content+'</body></html>')


def r3_controls_page(token):
    """Authenticated LAN dashboard for independent Bob R3, NOT legacy Scout."""
    try:
        from bob_r313d_package import load_verified
        load_verified()
    except (OSError,ValueError,ImportError,KeyError):
        return tab_page("Bob R3 Controls",
            '<p>R3 production package is not installed or does not match '
            'the updater registry. Owner controls remain unavailable.</p>')
    from bob_r313d_owner import (
        control_state, recent_proposals, trusted_manager_boundary,
    )
    with publish_conn() as db:
        trusted = trusted_manager_boundary(db)
        state = control_state(db) if trusted else {
            "schema":"unavailable", "manual":False, "automatic":False,
            "auto_ui_locked":True,
        }
        entries = recent_proposals(db, DATA) if (
            trusted and state["schema"] == "ready") else []
    notice = (
        '<p class="meta">The R3 schema is absent or host verification failed. '
        'Controls are read-only until the separately reviewed OFF-first install.</p>'
        if state["schema"] != "ready" else
        '<p class="meta">Bob-authored R3 uses independent owner consent. '
        'Legacy Scout approvals and existing autonomous posting DO NOT '
        'authorize Bob R3 comments. The publisher remains compiled OFF '
        'until separately approved release and canary.</p>'
    )
    csrf = esc(token)
    manual_on = bool(state["manual"])
    manual_action = "manual-off" if manual_on else "manual-on"
    phrase = "DISABLE R3 MANUAL" if manual_on else "ENABLE R3 MANUAL"
    action_label = "Disable Bob manual drafts" if manual_on else "Enable Bob manual review"
    controls = (
        f'<form method="post" action="/r3/mode/{manual_action}">'
        f'<input type="hidden" name="csrf" value="{csrf}">'
        f'<label>Type {esc(phrase)}: <input name="confirmation" '
        'autocomplete="off" required maxlength="48"></label>'
        f'<button>{esc(action_label)}</button></form>'
        f'<form method="post" action="/r3/mode/all-off">'
        f'<input type="hidden" name="csrf" value="{csrf}">'
        '<input type="hidden" name="confirmation" value="DISABLE R3">'
        '<button class="danger">Disable all Bob R3 publishing</button></form>'
        if state["schema"] == "ready" else ""
    )
    cards = []
    for item in entries:
        rid, digest = esc(item["run"]), esc(item["seal"])
        buttons = ""
        if item["status"] == "proposed":
            if item["approval"] == "none":
                buttons = ''.join(
                    f'<form method="post" action="/r3/review/{rid}/{op}">'
                    f'<input type="hidden" name="csrf" value="{csrf}">'
                    f'<input type="hidden" name="seal" value="{digest}">'
                    f'<button class="{cl}">{esc(label)}</button></form>'
                    for op, label, cl in (
                        ("approve","Approve exact Bob draft","secondary"),
                        ("reject","Reject exact Bob draft","danger")))
            elif item["approval"] == "approved" and manual_on:
                buttons = (
                    f'<form method="post" action="/r3/review/{rid}/queue">'
                    f'<input type="hidden" name="csrf" value="{csrf}">'
                    f'<input type="hidden" name="seal" value="{digest}">'
                    '<label>Type QUEUE BOB COMMENT: '
                    '<input name="confirmation" required maxlength="48" '
                    'autocomplete="off"></label>'
                    '<button>Queue approved draft (publisher still Off)</button>'
                    '</form>')
        cards.append(
            f'<article><h2>{esc(item["title"])}</h2>'
            f'<p class="meta">Source {rid} · {esc(item["author"])}'
            f' · Post ID {esc(item["post_id"])}</p>'
            f'<p>Bob reasoning: {esc(item["reason"])}</p>'
            f'<pre>{esc(item["text"])}</pre>'
            f'<p class="meta">Review {esc(item["approval"])}; '
            f'proposal {esc(item["status"])}; queue {esc(item["queue_state"])}; '
            f'attempt recorded {str(bool(item["attempted"]))}</p>'
            +buttons+'</article>')
    body = (
        '<p>R3 manual owner control: <b>' +
        ('ON (publisher separately gated)' if manual_on else 'OFF') +
        '</b>. R3 automatic publishing: <b>OFF (compiled locked)</b>.</p>' +
        notice + controls +
        '<h2>Independently sealed Bob drafts</h2>' +
        (''.join(cards) if cards else
         '<p>No eligible verified Bob proposals. Old Scout drafts never '
         'appear here as R3 drafts.</p>') +
        '<p class="meta">API acknowledgments are not independent public '
        'verification. Ambiguous sends are never automatically retried.</p>'
    )
    return tab_page("Bob R3 Controls", body)


class R3HandlerMixin:
    """Route-only extension: all unrecognized paths delegate to legacy Handler."""

    def do_GET(self):
        if urlsplit(self.path).path != "/r3":
            return super().do_GET()
        if not self._valid_host():
            self._send(403,"Unexpected Host header")
            return
        if not self._authenticated():
            self._auth_required()
            return
        self._send(200,r3_controls_page(self.R3_CSRF_TOKEN),
                   "text/html; charset=utf-8")

    def do_POST(self):
        path = urlsplit(self.path).path
        if not path.startswith("/r3/"):
            return super().do_POST()
        if not self._valid_host():
            self._send(403,"Unexpected Host header")
            return
        if not self._authenticated():
            self._auth_required()
            return
        if not self._valid_origin():
            self._error_page(403,"R3 action blocked",
                             "Origin or Host verification failed")
            return
        operation=re.fullmatch(
            r"/r3/mode/(manual-on|manual-off|auto-on|all-off)",path)
        review=re.fullmatch(
            r"/r3/review/(\d{8}T\d{6}Z)/(approve|reject|queue)",path)
        if not operation and not review:
            self._send(404,"Not found")
            return
        try:
            length=int(self.headers.get("Content-Length","-1"))
            if not 0 < length <= 1024:
                raise ValueError("r3_invalid_form_length")
            params=parse_qs(self.rfile.read(length).decode("utf-8"),
                            keep_blank_values=True)
            if any(len(values)!=1 for values in params.values()):
                raise ValueError("duplicate_r3_form_field")
            csrf=params.get("csrf",[""])[0]
            if not hmac.compare_digest(csrf,self.R3_CSRF_TOKEN):
                self._error_page(403,"R3 action blocked",
                                 "Expired CSRF token; reload the page")
                return
            from bob_r313d_package import load_verified
            load_verified()
            from bob_r313d_owner import (
                trusted_manager_boundary,set_owner_mode,decide_exact,
            )
            with publish_conn() as db:
                if not trusted_manager_boundary(db):
                    raise ValueError("untrusted_r3_manager_database")
                if operation:
                    set_owner_mode(db,operation.group(1),
                                   params.get("confirmation",[""])[0])
                else:
                    run,decision=review.groups()
                    if decision == "queue" and (
                            params.get("confirmation",[""])[0]
                            != "QUEUE BOB COMMENT"):
                        raise ValueError("explicit_r3_queue_confirmation_required")
                    decide_exact(db,DATA,run,params.get("seal",[""])[0],
                                 decision)
            self.send_response(303)
            self.send_header("Location","/r3")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,sqlite3.Error,OSError,TypeError,ImportError) as exc:
            reason=str(exc)
            if not re.fullmatch(r"[a-z0-9_]{3,64}",reason):
                reason="r3_action_unavailable"
            self._error_page(409,"Bob R3 action not completed",reason)
