"""R3.13d trusted OpenClaw Bob proposal writer: local-only, no Moltbook send.

The real command runs the EXISTING OpenClaw main agent against the exact saved
Scout observation. Only source-verified, independently sealed Bob comment
actions are added to the same private publisher DB, as PROPOSED, not queued.
The reader/model cannot change paths, target, permissions, API keys or schema.

This is a future installable Off-first worker, not a second publisher. The
R2 shadow worker remains independent and stores its own sanitized events.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import os
from pathlib import Path
import pwd
import sqlite3

from .core import Action, decision_prompt, parse_decision
from .evidence import latest_observations
from .r3_cutover_rehearsal import verified_source
from .r3_unified import _validated
from .r313c_candidate import canonical_action, MAX_ACTION_BYTES
from .shadow import openclaw_decide

MAX_SOURCE_AGE = timedelta(days=7)
NO_PRODUCTION_DISPATCH = True


@dataclass(frozen=True)
class ProposalResult:
    status: str
    reason: str
    source_run: str = ""
    queued: bool = False
    attempted: bool = False
    dispatch_authorized: bool = False


def propose_verified(db: sqlite3.Connection, source_dir: Path,
                     action: Action, *, at: datetime) -> ProposalResult:
    """Single atomic source/envelope/proposal write, never a publish job.

    The caller MUST be a fixed trusted producer, not an HTTP/model path input.
    This core is also exercised against synthetic offline fixtures in CI.
    """
    from bob_r313d_owner import schema_ready
    if not schema_ready(db):
        return ProposalResult("refused","r3_schema_not_ready")
    if at.tzinfo is None or at.utcoffset() is None:
        return ProposalResult("refused","invalid_proposal_clock")
    try:
        initial_obs, pin = verified_source(source_dir, action)
        seal, fingerprint = _validated(action, initial_obs)
        text = canonical_action(action)
        if not 0 < len(text.encode("utf-8")) <= MAX_ACTION_BYTES:
            return ProposalResult("refused","action_envelope_too_large")
        created = datetime.strptime(
            action.source_run,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        now_utc = at.astimezone(timezone.utc)
        if created > now_utc or now_utc - created > MAX_SOURCE_AGE:
            return ProposalResult("refused","proposal_source_expired")
    except (OSError, ValueError, TypeError, KeyError):
        return ProposalResult("refused","saved_source_or_action_invalid")
    db.execute("BEGIN IMMEDIATE")
    try:
        current_obs, second_pin = verified_source(
            source_dir, action, pinned=pin)
        second_seal, second_fingerprint = _validated(action, current_obs)
        if ((second_pin,second_seal,second_fingerprint)
                != (pin,seal,fingerprint)):
            raise ValueError("source_changed_at_proposal_commit")
        if db.execute(
            "SELECT 1 FROM r3_proposals WHERE source_run=? OR post_id=?",
            (action.source_run,action.target_id)).fetchone():
            raise ValueError("bob_proposal_or_target_already_seen")
        if db.execute(
            "SELECT 1 FROM publish_jobs WHERE run_id=? OR post_id=?",
            (action.source_run,action.target_id)).fetchone():
            raise ValueError("legacy_queue_target_already_seen")
        if db.execute(
            "SELECT 1 FROM decisions WHERE run_id=?",
            (action.source_run,)).fetchone():
            raise ValueError("legacy_approval_collision")
        stamp = now_utc.isoformat()
        db.execute(
            "INSERT INTO r313c_action_envelopes "
            "(source_run,action_json,action_sha256,seal_sha256,created_at)"
            " VALUES(?,?,?,?,?)",
            (action.source_run,text,hashlib.sha256(text.encode("utf-8")).hexdigest(),
             seal,stamp))
        db.execute(
            "INSERT INTO r3_proposals "
            "(source_run,post_id,draft_comment,seal_sha256,fingerprint,"
            "snapshot_sha256,state,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,'proposed',?,?)",
            (action.source_run,action.target_id,action.text,seal,
             fingerprint,pin.snapshot_sha256,stamp,stamp))
        db.execute(
            "INSERT INTO r3_lab_audit(source_run,event,reason,at)"
            " VALUES(?,?,?,?)",
            (action.source_run,"r313d_proposal",
             "bob_validated_comment_no_queue_or_send",stamp))
        db.commit()
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        db.rollback()
        # Do not log source post text, Bob draft, API keys or model response.
        return ProposalResult("refused","proposal_conflict_or_source_changed")
    return ProposalResult("proposed","awaits_separate_owner_review",
                          source_run=action.source_run)


def run_one(*, model=openclaw_decide, clock=None) -> ProposalResult:
    """Fixed real host entry: one fresh verified Scout selection; no POST.

    The function does not accept filesystem or DB paths from CLI/model.
    """
    from bob_publish_common import DATA, DB, connect
    from bob_r313d_owner import trusted_manager_boundary, schema_ready
    home = Path.home()
    uid = os.geteuid()
    if uid == 0 or pwd.getpwuid(uid).pw_dir != str(home):
        return ProposalResult("refused","untrusted_producer_account")
    instant = datetime.now(timezone.utc) if clock is None else clock()
    if not isinstance(instant,datetime) or instant.tzinfo is None:
        return ProposalResult("refused","invalid_producer_clock")
    if DATA.is_symlink() or not DATA.is_dir() or DATA.stat().st_mode & 0o077:
        return ProposalResult("refused","untrusted_saved_source_root")
    with connect() as db:
        if not trusted_manager_boundary(db) or not schema_ready(db):
            return ProposalResult("refused","production_schema_or_host_unavailable")
        sources = latest_observations(DATA,limit=8)
        chosen = None
        for obs in sources:
            try:
                created = datetime.strptime(
                    obs.run_id,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                if created > instant or instant-created > MAX_SOURCE_AGE:
                    continue
                if db.execute(
                    "SELECT 1 FROM r3_proposals WHERE source_run=? OR post_id=?",
                    (obs.run_id,obs.post_id)).fetchone():
                    continue
                if db.execute(
                    "SELECT 1 FROM publish_jobs WHERE run_id=? OR post_id=?",
                    (obs.run_id,obs.post_id)).fetchone():
                    continue
                chosen = obs
                break
            except (OSError,ValueError,sqlite3.Error,TypeError):
                continue
        if chosen is None:
            return ProposalResult("none","no_fresh_unseen_source")
        try:
            output = model(
                decision_prompt(chosen), "moltbook-v08-shadow-r3-propose-"+chosen.run_id)
            action = parse_decision(output,chosen)
        except (OSError,RuntimeError,ValueError,TypeError):
            return ProposalResult("refused","openclaw_decision_invalid_or_unavailable")
        if action.kind == "skip":
            return ProposalResult("skipped","bob_chose_not_to_comment",
                                  source_run=chosen.run_id)
        return propose_verified(db,DATA,action,at=instant)


def main(argv=None):
    import json
    import sys
    options = sys.argv[1:] if argv is None else argv
    if options != ["--once"]:
        print("Usage: bob-r3-propose --once")
        return 2
    try:
        result=run_one()
        print(json.dumps(result.__dict__,sort_keys=True))
        return 0 if result.status in ("proposed","skipped","none") else 1
    except (OSError,sqlite3.Error,ValueError,RuntimeError):
        print('{"status":"refused","reason":"producer_unavailable",'
              '"queued":false,"attempted":false,"dispatch_authorized":false}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
