#!/usr/bin/env python3
"""Read-only Bob comment queue diagnosis. Does not publish, approve, or modify jobs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys

DB = Path.home() / ".config/moltbook/activity-queue.sqlite3"
PAUSED = Path.home() / ".config/bob-system/paused"
PUBLISHER = Path.home() / ".local/bin/bob-moltbook-publisher"
DAILY_MAX = 2
MIN_GAP = timedelta(hours=1)


def parsed_time(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def diagnose(path=DB, *, at=None, paused=None):
    """Return bounded policy and queue facts from a SQLite read-only transaction."""
    stamp = at or datetime.now(timezone.utc)
    is_paused = PAUSED.exists() if paused is None else paused
    if path.is_symlink() or not path.is_file():
        raise ValueError("queue database unavailable")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2) as db:
        db.execute("PRAGMA query_only=ON")
        modes = {
            (mode, state): count
            for mode, state, count in db.execute(
                "SELECT mode,state,COUNT(*) FROM publish_jobs GROUP BY mode,state")
        }
        auto_setting = db.execute(
            "SELECT value FROM publish_settings WHERE name='auto_enabled'").fetchone()
        auto_enabled = bool(auto_setting and auto_setting[0] == "1")
        today = stamp.strftime("%Y-%m-%d")
        attempts = db.execute(
            "SELECT COUNT(*) FROM publish_jobs WHERE attempted_at LIKE ?",
            (today + "%",)).fetchone()[0]
        row = db.execute(
            "SELECT attempted_at FROM publish_jobs WHERE attempted_at IS NOT NULL "
            "ORDER BY attempted_at DESC LIMIT 1").fetchone()
        last_attempt = parsed_time(row[0]) if row else None
        head = db.execute(
            "SELECT run_id,mode,created_at FROM publish_jobs WHERE state='queued' "
            "ORDER BY created_at ASC LIMIT 1").fetchone()
        manual = db.execute(
            "SELECT run_id,mode,created_at FROM publish_jobs WHERE state='queued' "
            "AND mode='manual' ORDER BY created_at ASC LIMIT 1").fetchone()
        manual_count = sum(n for (mode, state), n in modes.items()
                           if mode == "manual" and state == "queued")
        auto_count = sum(n for (mode, state), n in modes.items()
                         if mode == "auto" and state == "queued")
    # Inspection only: the development checkout may be newer than the installed
    # publisher. Show which ordering policy the running worker will load next.
    installed_manual_first = False
    try:
        if not PUBLISHER.is_symlink() and PUBLISHER.is_file() and PUBLISHER.stat().st_size < 100000:
            installed_manual_first = "CASE WHEN mode='manual' THEN 0 ELSE 1 END" in PUBLISHER.read_text(
                encoding="utf-8", errors="replace")
    except OSError:
        pass
    until = None
    reason = "eligible under local posting-rate policy"
    if is_paused:
        reason = "Bob is paused"
    elif attempts >= DAILY_MAX:
        until = (stamp + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        reason = "daily comment attempt limit reached"
    elif last_attempt and stamp - last_attempt < MIN_GAP:
        until = last_attempt + MIN_GAP
        reason = "minimum interval between posting attempts"
    elif not head:
        reason = "no queued comment jobs"
    elif head[1] == "auto" and not auto_enabled and not installed_manual_first:
        reason = "oldest queued job is disabled auto; blocks newer manual jobs"
    return {
        "utc_time": stamp.isoformat(timespec="seconds"),
        "paused": bool(is_paused),
        "auto_enabled": auto_enabled,
        "attempts_today": attempts,
        "daily_limit": DAILY_MAX,
        "last_attempt_utc": last_attempt.isoformat(timespec="seconds") if last_attempt else None,
        "next_rate_slot_utc": until.isoformat(timespec="seconds") if until else None,
        "queued_manual": manual_count,
        "queued_auto": auto_count,
        "oldest_queued": {"id": head[0], "mode": head[1], "created_at": head[2]} if head else None,
        "oldest_manual": {"id": manual[0], "created_at": manual[2]} if manual else None,
        "manual_behind_auto": bool(head and manual and head[1] == "auto" and not installed_manual_first),
        "manual_first_installed": installed_manual_first,
        "queue_state_counts": {
            mode + "/" + state: count for (mode, state), count in sorted(modes.items())
        },
        "reason": reason,
    }


def main():
    try:
        report = diagnose()
    except (ValueError, OSError, sqlite3.Error) as exc:
        print("COMMENT QUEUE DIAGNOSIS: REFUSED (" + type(exc).__name__ + ")")
        return 1
    print("COMMENT QUEUE DIAGNOSIS (read-only; no publishing)")
    for name in ("utc_time", "paused", "auto_enabled", "attempts_today",
                 "daily_limit", "last_attempt_utc", "next_rate_slot_utc",
                 "queued_manual", "queued_auto", "oldest_queued",
                 "oldest_manual", "manual_behind_auto", "manual_first_installed", "reason"):
        print(name + ": " + str(report[name]))
    print("States:")
    for key, count in report["queue_state_counts"].items():
        print("  " + key + ": " + str(count))
    print("Rate limits and queue order are read from reviewed source policy; "
          "this does not contact Moltbook.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
