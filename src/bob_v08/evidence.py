"""Source-verified legacy Scout observations and an append-only shadow ledger.

No HTTP clients, Moltbook credentials, publisher imports or write access to the
legacy queue. Each legacy observation is validated against the saved feed bytes.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import sqlite3

from .core import Observation, RUN_ID, UUID

SHA256 = re.compile(r"[a-f0-9]{64}\Z")
STATES = frozenset(("seen", "decided", "checked", "skipped", "invalid", "reflected", "paused"))
KINDS = frozenset(("observe", "decision", "policy", "agent_error", "reflection", "pause"))
SCHEMA = 1
MAX_RAW = 512 * 1024
MAX_REPORT = 1024 * 1024


def _file(path: Path, cap: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("invalid_source_file")
    if not 0 < path.stat().st_size <= cap:
        raise ValueError("invalid_source_size")
    return path.read_bytes()


def read_observation(directory: Path, run_id: str) -> Observation:
    """Verify an old Scout result; never accept arbitrary paths from the model."""
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("invalid_source_run")
    directory = Path(directory)
    result = json.loads(_file(directory / ("scout-result-" + run_id + ".json"),
                              MAX_REPORT))
    feed_raw = _file(directory / ("scout-feed-" + run_id + ".json"), MAX_RAW)
    digest = hashlib.sha256(feed_raw).hexdigest()
    if (not isinstance(result, dict) or result.get("run_id") != run_id
            or result.get("schema") != 2
            or result.get("snapshot_file") != "scout-feed-" + run_id + ".json"
            or result.get("snapshot_sha256") != digest):
        raise ValueError("unverified_source_record")
    post_id = result.get("chosen_post_id")
    approval = result.get("approval_sha256")
    draft = result.get("draft_comment")
    if (not isinstance(post_id, str) or not UUID.fullmatch(post_id)
            or not isinstance(draft, str) or not draft.strip()
            or not isinstance(approval, str) or not SHA256.fullmatch(approval)
            or result.get("draft_sha256") != hashlib.sha256(draft.encode()).hexdigest()
            or approval != hashlib.sha256((post_id + "\n" + draft + "\n" +
                                          digest).encode()).hexdigest()):
        raise ValueError("unverified_source_draft")
    feed = json.loads(feed_raw)
    if not isinstance(feed, dict) or not isinstance(feed.get("posts"), list):
        raise ValueError("invalid_source_feed")
    posts = [p for p in feed["posts"] if isinstance(p, dict) and p.get("id") == post_id]
    if len(posts) != 1:
        raise ValueError("source_post_not_found")
    post = posts[0]
    if not all(isinstance(post.get(k), str) for k in ("title", "author", "content")):
        raise ValueError("invalid_source_fields")
    when = feed.get("fetched_at", "")
    if not isinstance(when, str) or len(when) > 45:
        when = ""
    return Observation(
        run_id, post_id, post["author"][:80], post["title"][:160],
        post["content"][:1200], digest, approval, when)


def latest_observations(directory: Path, *, max_scan: int = 40,
                        limit: int = 8) -> tuple[Observation, ...]:
    """Inspect only bounded files; invalid/unsealed reports are omitted."""
    directory = Path(directory)
    if max_scan < 1 or max_scan > 100 or limit < 1 or limit > 20:
        raise ValueError("invalid_limits")
    if directory.is_symlink() or not directory.is_dir():
        return ()
    output = []
    paths = sorted(directory.glob("scout-result-*.json"), reverse=True)
    for path in paths[:max_scan]:
        name = path.name
        match = re.fullmatch(r"scout-result-([0-9]{8}T[0-9]{6}Z)\.json", name)
        if not match:
            continue
        try:
            output.append(read_observation(directory, match.group(1)))
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            continue
        if len(output) == limit:
            break
    return tuple(output)


class EventStore:
    """Private, separate R2 DB; no migration to v0.7 publication data."""
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def open(self):
        parent = self.path.parent
        if self.path.is_symlink() or parent.is_symlink():
            raise ValueError("unsafe_shadow_path")
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if parent.stat().st_mode & 0o077:
            raise ValueError("shadow_directory_not_private")
        if self.path.exists() and (not self.path.is_file()
                                   or self.path.stat().st_mode & 0o077):
            raise ValueError("shadow_database_not_private")
        previous = os.umask(0o077)
        try:
            db = sqlite3.connect(self.path, timeout=5)
        finally:
            os.umask(previous)
        try:
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT NOT NULL, source_run TEXT NOT NULL, post_id TEXT NOT NULL,
                kind TEXT NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL,
                action_type TEXT NOT NULL, correlation TEXT UNIQUE
            )""")
            db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('schema','1')")
            row = db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            if row != (str(SCHEMA),):
                raise ValueError("shadow_schema_mismatch")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def append(db, *, source_run: str, post_id: str, kind: str, state: str,
               reason: str, action_type: str = "skip", correlation: str | None = None):
        if (kind not in KINDS or state not in STATES
                or not RUN_ID.fullmatch(source_run) or not UUID.fullmatch(post_id)
                or action_type not in (("comment", "skip", "unknown")
                                       if kind == "agent_error" else ("comment", "skip")) or
                not isinstance(reason, str) or not re.fullmatch(r"[a-z0-9_]{1,56}", reason)):
            raise ValueError("invalid_event")
        if correlation is not None and (
                not isinstance(correlation, str) or
                not re.fullmatch(r"[a-f0-9]{64}", correlation)):
            raise ValueError("invalid_correlation")
        db.execute("INSERT OR IGNORE INTO events(at,source_run,post_id,kind,state,"
                   "reason,action_type,correlation) VALUES(?,?,?,?,?,?,?,?)",
                   (datetime.now(timezone.utc).isoformat(), source_run, post_id,
                    kind, state, reason, action_type, correlation))

    @staticmethod
    def previously_decided(db, source_run: str, post_id: str) -> bool:
        return db.execute("SELECT 1 FROM events WHERE source_run=? AND post_id=? "
                          "AND kind IN ('decision','agent_error') LIMIT 1",
                          (source_run, post_id)).fetchone() is not None

    @staticmethod
    def recent(db, count: int = 20) -> list[dict]:
        if type(count) is not int or count < 1 or count > 50:
            raise ValueError("invalid_event_limit")
        rows = db.execute("SELECT at,source_run,post_id,kind,state,reason,action_type "
                          "FROM events ORDER BY id DESC LIMIT ?", (count,)).fetchall()
        return [dict(zip(("at", "source_run", "post_id", "kind", "state",
                          "reason", "action_type"), row)) for row in rows]
