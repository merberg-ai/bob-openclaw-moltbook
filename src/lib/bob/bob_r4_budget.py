"""R4 counted-attempt budgets across the existing SINGLE publisher.

These are fixed conservative source limits, not owner-mode authorization.
Only timestamps from durable local ledgers count, including unknown, failed
or interrupted attempts. A malformed or future attempted timestamp holds
the entire R4 candidate. All checks run again inside BEGIN IMMEDIATE before
recording the R4 attempt, never on an unverified or model-supplied date.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import sqlite3

R4_GLOBAL_DAILY_CAP=4
R4_MIN_GAP=timedelta(minutes=20)
SOURCE_TABLES=("r4_action_outbox","publish_jobs","original_posts")


@dataclass(frozen=True)
class Budget:
    allowed:bool
    reason:str
    used_today:int=0
    last_attempt:datetime|None=None


def inspect(db:sqlite3.Connection,*,at:datetime)->Budget:
    if type(at) is not datetime or at.tzinfo is None:
        return Budget(False,"invalid_budget_clock")
    stamp=at.astimezone(timezone.utc)
    try:
        names={row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('r4_action_outbox','publish_jobs','original_posts')")}
        if "r4_action_outbox" not in names or "publish_jobs" not in names:
            return Budget(False,"required_attempt_ledger_unavailable")
        attempts=[]
        for table in SOURCE_TABLES:
            if table not in names:
                continue
            values=db.execute(
                "SELECT attempted_at FROM "+table+
                " WHERE attempted_at IS NOT NULL").fetchall()
            if len(values)>200000:
                return Budget(False,"unbounded_attempt_history")
            for (raw,) in values:
                if type(raw) is not str or len(raw)>64:
                    return Budget(False,"malformed_attempt_history")
                try:
                    t=datetime.fromisoformat(raw.replace("Z","+00:00"))
                except (ValueError,TypeError,OverflowError):
                    return Budget(False,"malformed_attempt_history")
                if t.tzinfo is None:
                    return Budget(False,"untrusted_attempt_timezone")
                utc=t.astimezone(timezone.utc)
                if utc>stamp:
                    return Budget(False,"attempt_clock_future")
                attempts.append(utc)
        today=stamp.date()
        used=sum(x.date()==today for x in attempts)
        latest=max(attempts) if attempts else None
        if used>=R4_GLOBAL_DAILY_CAP:
            return Budget(False,"r4_global_counted_daily_cap",used,latest)
        if latest is not None and stamp-latest<R4_MIN_GAP:
            return Budget(False,"r4_global_counted_cooldown",used,latest)
        return Budget(True,"counted_budget_clear",used,latest)
    except (OSError,ValueError,sqlite3.Error,TypeError):
        return Budget(False,"counted_budget_unavailable")
