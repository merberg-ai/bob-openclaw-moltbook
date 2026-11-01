"""R4 verified Bob-expressed opinion snapshot, never manufactured memories.

An independently sealed R3 action reason is a genuine prior Bob expression,
not an owner-confirmed fact or an authenticated remote relationship.
This adapter does not feed a new model, mutate PM2, or create publish jobs.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3

from bob_publish_common import DATA,DB

MAX=8


def reasons(*,path:Path=DB,source:Path=DATA,limit:int=MAX) -> list[dict]:
    if type(limit) is not int or not 1<=limit<=MAX:
        raise ValueError("r4_invalid_reason_limit")
    from bob_r313d_package import load_verified
    if load_verified()!="verified_registry_archive":
        return []
    from bob_r313d_owner import (
        recent_proposals, trusted_manager_boundary, control_state)
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        return []
    try:
        with closing(sqlite3.connect(path.absolute().as_uri()+"?mode=ro",
                                     uri=True,timeout=3)) as db:
            db.execute("PRAGMA query_only=ON")
            if not trusted_manager_boundary(db):
                return []
            state=control_state(db)
            if state["schema"]!="ready":
                return []
            rows=recent_proposals(db,source,limit=limit)
        output=[]
        for row in rows:
            if not isinstance(row,dict):
                continue
            rid=row.get("run")
            reason=row.get("reason")
            if (not isinstance(rid,str) or not isinstance(reason,str)
                    or not reason.strip() or len(reason)>260):
                continue
            output.append({
                "source_run":rid,
                "topic":str(row.get("title") or "Untitled discussion")[:180],
                "reason":reason,
                "context":"Bob's sealed R3 choice, not an independently verified fact",
                "confidence":"expressed_by_bob_not_owner_confirmed",
                "published_state":str(row.get("status") or "unknown")[:32],
            })
        return output
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,ImportError):
        return []
