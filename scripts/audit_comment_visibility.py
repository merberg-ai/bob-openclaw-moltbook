#!/usr/bin/env python3
"""Read-only, bounded audit of Bob's comment IDs against public Moltbook threads.

No Moltbook credentials loaded, no write methods, no SQLite mutations.
Absence in a public listing is NOT proof of deletion or failure; filtering,
moderation and pagination may prevent visibility.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.moltbook.com/api/v1"
DB = Path.home() / ".config/moltbook/activity-queue.sqlite3"
UUID = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\Z")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected redirect")


def contains_comment(nodes, target, max_nodes=1200):
    """Search the bounded visible tree by exact ID, never by body text."""
    if not isinstance(nodes, list):
        return False
    stack = list(reversed(nodes[:100]))
    examined = 0
    while stack and examined < max_nodes:
        node = stack.pop()
        examined += 1
        if not isinstance(node, dict):
            continue
        if node.get("id") == target:
            return True
        children = node.get("replies")
        if isinstance(children, list):
            stack.extend(reversed(children[:100]))
    return False


def audit_one(post_id, comment_id, *, max_pages=3, opener=None):
    if not UUID.fullmatch(post_id) or not UUID.fullmatch(comment_id):
        return "id_unconfirmed"
    loader = opener or urllib.request.build_opener(NoRedirect())
    cursor = None
    for _ in range(max_pages):
        uri = BASE + "/posts/" + post_id + "/comments?sort=new&limit=100"
        if cursor:
            uri += "&cursor=" + urllib.parse.quote(cursor, safe="")
        request = urllib.request.Request(
            uri, headers={"Accept": "application/json", "User-Agent": "BobLocalVisibilityAudit/1.0"})
        try:
            with loader.open(request, timeout=8) as response:
                if response.status != 200:
                    return "public_check_unavailable"
                payload = response.read(256 * 1024 + 1)
            if len(payload) > 256 * 1024:
                return "public_check_unavailable"
            data = json.loads(payload)
            if not isinstance(data, dict):
                return "public_check_unavailable"
            body = data.get("data") if isinstance(data.get("data"), dict) else data
            comments = body.get("comments")
            if not isinstance(comments, list):
                return "public_check_unavailable"
            if contains_comment(comments, comment_id):
                return "visible_in_public_listing"
            more = body.get("has_more")
            next_cursor = body.get("next_cursor")
            if more is False:
                return "not_observed_in_public_listing"
            if not isinstance(next_cursor, str) or not 0 < len(next_cursor) <= 256 or next_cursor == cursor:
                return "scan_incomplete"
            cursor = next_cursor
        except (OSError, ValueError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            return "public_check_unavailable"
    return "scan_incomplete"


def audit(path=DB, *, max_jobs=5, max_pages=3, opener=None):
    if path.is_symlink() or not path.is_file():
        raise ValueError("private database unavailable")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2) as db:
        db.execute("PRAGMA query_only=ON")
        records = db.execute(
            "SELECT run_id, post_id, comment_id, state FROM publish_jobs "
            "WHERE state IN ('published','verified_unconfirmed') "
            "ORDER BY attempted_at DESC LIMIT ?", (max_jobs,)).fetchall()
    return [{"job_id": rid, "state": state,
             "public_observation": audit_one(pid, cid, max_pages=max_pages, opener=opener)
             if isinstance(pid, str) and isinstance(cid, str) else "id_unconfirmed"}
            for rid, pid, cid, state in records]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-jobs", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.max_jobs <= 10 or not 1 <= args.max_pages <= 5:
        parser.error("job/page limits are 1-10 jobs and 1-5 pages")
    try:
        result = audit(max_jobs=args.max_jobs, max_pages=args.max_pages)
    except (OSError, ValueError, sqlite3.Error):
        print("PUBLIC COMMENT AUDIT: REFUSED; database unavailable")
        return 1
    print("PUBLIC COMMENT AUDIT (read-only; no Moltbook writes):")
    if not result:
        print("No recently acknowledged comment jobs")
    for item in result:
        print(item["job_id"] + ": " + item["state"] + " => " + item["public_observation"])
    print("Not observed is NOT proof of deletion; no posts will be retried.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
