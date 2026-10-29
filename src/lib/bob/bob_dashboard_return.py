"""Allowlisted destinations for Bob's Scout action POST/Redirect/GET.

Submitted destinations are always local, canonical Scout routes. Never accept
external redirect targets or use an unchecked Referer/Origin for navigation.
This module does not mutate state.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlsplit

STATES = frozenset(("pending", "all", "approved", "rejected", "needs review",
                    "queued", "awaiting_verification", "published", "failed",
                    "cancelled"))
VISIBILITY = frozenset(("active", "archived", "all"))
RUN_ID = re.compile(r"\d{8}T\d{6}Z\Z")
PAGE = re.compile(r"[1-9][0-9]{0,3}\Z")
FIELDS = frozenset(("state", "show", "q", "page"))


def scout_destination(form, run_id=None):
    """Validate form['return_to'], return Scout-local URL and optional safe anchor.

    Called before processing any action, so a malformed target cannot cause a
    successful write followed by a misleading redirect error.
    """
    values = form.get("return_to", [])
    if not values:
        target = "/scout"
    elif len(values) != 1 or not isinstance(values[0], str):
        raise ValueError("invalid Scout return target")
    else:
        target = values[0]
    if len(target) > 1024 or any(ord(ch) < 32 or ord(ch) == 127 for ch in target):
        raise ValueError("invalid Scout return target")
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or parsed.fragment or parsed.path not in ("/scout", "/scout/full"):
        raise ValueError("unsafe Scout return target")
    path = parsed.path
    if path == "/scout/full":
        if parsed.query:
            raise ValueError("full Scout history has no filters")
    elif parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=4)
        if not set(params).issubset(FIELDS) or any(len(v) != 1 for v in params.values()):
            raise ValueError("unexpected Scout filter")
        if ("state" in params and params["state"][0] not in STATES
                or "show" in params and params["show"][0] not in VISIBILITY
                or "page" in params and not PAGE.fullmatch(params["page"][0])
                or "q" in params and len(params["q"][0]) > 64):
            raise ValueError("invalid Scout filter")
        path += "?" + urlencode({k: params[k][0] for k in ("state", "show", "q", "page")
                                  if k in params})
    if run_id is not None:
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise ValueError("invalid run anchor")
        path += "#run-" + run_id
    return path


def section_for_action(action_path):
    """Static navigation for errors, never a client-controlled location."""
    path = urlsplit(action_path).path
    if (path.startswith("/review/") or path.startswith("/publish/")
            or path.startswith("/verify/") or path.startswith("/autopost/")):
        return "/scout"
    if path.startswith("/original/") or path.startswith("/originals/request/"):
        return "/originals"
    if path == "/manage/bulk":
        return "/manage"
    if path == "/settings/password":
        return "/settings/users"
    if path == "/settings/activity-limits":
        return "/settings/activity-limits"
    return "/"
