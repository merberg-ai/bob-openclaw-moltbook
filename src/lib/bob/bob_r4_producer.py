"""R4 one-shot proposal producer: existing OpenClaw Bob, NO public writer.

This is a source-only future candidate, not an installed or enabled timer.
The single trusted host input is the established sealed Scout feed. No user or
model-controlled URL, key, filename, post target, or SQL may enter this worker.
R4 defaults to Off AND paused. A future explicit migration + owner opt-in is
required before a model is called, and a proposal never enqueues a public job.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
import os
import pwd
import re
import sqlite3

from bob_publish_common import connect,DATA
from bob_r4_agent import decide,AVAILABLE
from bob_r4_controls import read_modes,pause_state
from bob_r4_ledger import record,schema_ready,author_count
from bob_r4_decision import SOURCE_AGE

@dataclass(frozen=True)
class Result:
    status:str
    reason:str
    source_run:str=""
    queued:bool=False
    attempted:bool=False
    dispatch_authorized:bool=False


def run_one(*,model=None,clock=None,observations=None) -> Result:
    """Natural one-source decision; injectable model and sources for CI ONLY."""
    now=datetime.now(timezone.utc) if clock is None else clock()
    if type(now) is not datetime or now.tzinfo is None:
        return Result("refused","invalid_r4_clock")
    try:
        from bob_r313d_package import load_verified
        if load_verified()!="verified_registry_archive":
            return Result("refused","unverified_r3_source_archive")
        from bob_v08.evidence import latest_observations
        from bob_v08.shadow import openclaw_decide
        from bob_r313d_owner import trusted_manager_boundary
        home=Path.home()
        uid=os.geteuid()
        if uid==0 or pwd.getpwuid(uid).pw_dir!=str(home):
            return Result("refused","untrusted_r4_account")
        if (DATA.is_symlink() or not DATA.is_dir() or
                DATA.stat().st_uid!=uid or DATA.stat().st_mode & 0o077):
            return Result("refused","untrusted_r4_saved_feed_root")
        if model is None:
            model=openclaw_decide
        if not callable(model):
            return Result("refused","invalid_r4_agent_transport")
        with connect() as db:
            if not trusted_manager_boundary(db) or not schema_ready(db):
                return Result("refused","r4_private_schema_or_host_unverified")
            try:
                modes=read_modes(db)
                paused=pause_state(db)
            except (ValueError,sqlite3.Error):
                return Result("refused","r4_settings_unverified")
            if paused or not any(modes[x]=="propose" for x in AVAILABLE):
                return Result("none","r4_paused_or_all_actions_off")
            choices=(
                latest_observations(DATA,max_scan=100,limit=20)
                if observations is None else observations)
            if not isinstance(choices,(tuple,list)) or len(choices)>20:
                return Result("refused","invalid_r4_source_window")
            selected=None
            for item in choices:
                try:
                    created=datetime.strptime(item.run_id,"%Y%m%dT%H%M%SZ").replace(
                        tzinfo=timezone.utc)
                    age=now.astimezone(timezone.utc)-created
                    if not 0<=age<=SOURCE_AGE:
                        continue
                    if db.execute(
                        "SELECT 1 FROM r4_social_decisions WHERE source_run=?",
                        (item.run_id,)).fetchone():
                        continue
                    if db.execute(
                        "SELECT 1 FROM r3_proposals WHERE source_run=?",
                        (item.run_id,)).fetchone():
                        continue
                    if db.execute(
                        "SELECT 1 FROM publish_jobs WHERE run_id=?",
                        (item.run_id,)).fetchone():
                        continue
                    selected=item
                    break
                except (ValueError,TypeError,AttributeError,sqlite3.Error):
                    continue
            if selected is None:
                return Result("none","no_fresh_r4_source")
            try:
                decision=decide(
                    selected,modes=modes,model=model,now=now,
                    author_observations=author_count(DATA,selected))
            except (OSError,ValueError,TypeError,RuntimeError):
                # Invalid OpenClaw output is NOT a legitimate skip and must
                # NEVER consume a source or expose raw model/private text.
                return Result("refused","r4_model_or_contract_unverified",
                              source_run=selected.run_id)
            try:
                state=record(db,DATA,selected,decision,at=now)
            except (OSError,ValueError,sqlite3.Error,TypeError,KeyError):
                return Result("refused","r4_source_or_owner_gate_changed",
                              source_run=selected.run_id)
            return Result(state,
                          "bob_abstained" if state=="skipped"
                          else "private_owner_review_only",
                          source_run=selected.run_id)
    except (OSError,ValueError,sqlite3.Error,TypeError,KeyError,
            ImportError,AttributeError):
        return Result("refused","r4_verified_host_unavailable")


def main(argv=None):
    import json
    import sys
    args=sys.argv[1:] if argv is None else argv
    if args!=["--once"]:
        print("Usage: bob-r4-propose --once")
        return 2
    item=run_one()
    print(json.dumps(item.__dict__,sort_keys=True,separators=(",",":")))
    return 0 if item.status in ("none","skipped","proposed") else 1


if __name__=="__main__":
    raise SystemExit(main())
