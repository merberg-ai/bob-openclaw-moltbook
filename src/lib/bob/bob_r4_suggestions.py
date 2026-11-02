"""Owner-reviewed evidence-backed R4 memory and relationship suggestions.

Only a source-verified Bob R4 decision may generate a private suggestion.
Stage is called INSIDE bob_r4_ledger's existing BEGIN IMMEDIATE transaction.
Review uses a new transaction, exact suggestion seal and typed owner consent.
Memory approval creates a LOW-confidence, owner-reviewed PM2 note; relationship
approval only stages a candidate in the EXISTING Friend Discovery review flow.
Neither creates a Moltbook follow, post, publisher job or OpenClaw memory file.

The tables are installed ONLY by an explicit future migration, never GET.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import hmac
import json
import re
import sqlite3

FORMAT="r4-evidence-suggestion-v1"
KINDS=("memory","relationship")
RUN=re.compile(r"\d{8}T\d{6}Z\Z")
SHA=re.compile(r"[a-f0-9]{64}\Z")
MAX_ITEMS=300
MAX_PENDING=60
MAX_LIST=20
COLUMNS=frozenset((
    "source_run","kind","decision_seal","source_post","source_author",
    "title","detail","seal_sha256","state","created_at","reviewed_at",
    "applied_ref"))
REVIEW_COLUMNS=frozenset((
    "source_run","kind","seal_sha256","decision","at","applied_ref"))


def initialize(db:sqlite3.Connection) -> None:
    """Additive idempotent migration. Caller must run only during install."""
    db.execute("""CREATE TABLE IF NOT EXISTS r4_evidence_suggestions (
      source_run TEXT NOT NULL,kind TEXT NOT NULL
        CHECK(kind IN ('memory','relationship')),
      decision_seal TEXT NOT NULL,source_post TEXT NOT NULL,
      source_author TEXT NOT NULL,title TEXT NOT NULL,detail TEXT NOT NULL,
      seal_sha256 TEXT NOT NULL,state TEXT NOT NULL
        CHECK(state IN ('pending','approved','rejected')),
      created_at TEXT NOT NULL,reviewed_at TEXT NOT NULL,
      applied_ref TEXT NOT NULL,PRIMARY KEY(source_run,kind))""")
    db.execute("""CREATE TABLE IF NOT EXISTS r4_evidence_reviews (
      source_run TEXT NOT NULL,kind TEXT NOT NULL,seal_sha256 TEXT NOT NULL,
      decision TEXT NOT NULL CHECK(decision IN ('approved','rejected')),
      at TEXT NOT NULL,applied_ref TEXT NOT NULL,
      PRIMARY KEY(source_run,kind))""")
    db.execute("CREATE INDEX IF NOT EXISTS r4_evidence_state_idx "
               "ON r4_evidence_suggestions(state,created_at)")


def schema_ready(db:sqlite3.Connection) -> bool:
    try:
        expected={
            "r4_evidence_suggestions":COLUMNS,
            "r4_evidence_reviews":REVIEW_COLUMNS}
        for table,columns in expected.items():
            observed={r[1] for r in db.execute(
                "PRAGMA table_info("+table+")")}
            if observed!=columns:
                return False
        return True
    except sqlite3.Error:
        return False


def _payload(observed,decision,decision_seal,kind):
    if kind=="memory":
        if not isinstance(decision.reason,str) or len(decision.reason.strip())<8:
            return None
        title=("Bob observed: "+str(observed.title).strip())[:120]
        # The original Bob reason is saved exactly. It is an opinion, not a
        # verified fact, and is NEVER silently fed into the main-agent memory.
        detail=decision.reason.strip()
    elif kind=="relationship":
        if (decision.kind!="follow" or
                decision.target_id!=observed.author):
            return None
        from bob_friends import handle
        handle(observed.author)
        title="Review observed agent @"+observed.author
        detail=decision.reason.strip()
    else:
        raise ValueError("r4_suggestion_type_unknown")
    return dict(source_run=observed.run_id,kind=kind,
                decision_seal=decision_seal,source_post=observed.post_id,
                source_author=observed.author,title=title,detail=detail)


def _seal(payload):
    return hashlib.sha256(json.dumps(
        {"format":FORMAT,**payload},sort_keys=True,
        ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()


def auto_stage(db:sqlite3.Connection,observed,decision,decision_seal,stamp:str):
    """Use only an already verified actual Bob decision in parent transaction.

    No BEGIN, COMMIT, DDL or network here. Any stage failure rolls back the
    complete parent source-ledger insertion rather than leaving split state.
    """
    if not schema_ready(db):
        raise ValueError("r4_suggestion_schema_not_installed")
    if decision.kind=="skip":
        return ()
    if not SHA.fullmatch(decision_seal):
        raise ValueError("r4_untrusted_decision_seal")
    count,pending=db.execute(
        "SELECT COUNT(*),SUM(CASE WHEN state='pending' THEN 1 ELSE 0 END)"
        " FROM r4_evidence_suggestions").fetchone()
    candidates=[]
    for kind in KINDS:
        item=_payload(observed,decision,decision_seal,kind)
        if item is not None:
            candidates.append(item)
    if count+len(candidates)>MAX_ITEMS or (pending or 0)+len(candidates)>MAX_PENDING:
        raise ValueError("r4_suggestion_capacity_reached")
    for item in candidates:
        db.execute(
            "INSERT INTO r4_evidence_suggestions "
            "(source_run,kind,decision_seal,source_post,source_author,title,"
            "detail,seal_sha256,state,created_at,reviewed_at,applied_ref)"
            " VALUES(?,?,?,?,?,?,?,?,'pending',?,'','')",
            (item["source_run"],item["kind"],item["decision_seal"],
             item["source_post"],item["source_author"],item["title"],
             item["detail"],_seal(item),stamp))
    return tuple(x["kind"] for x in candidates)


def _checked(db,source_dir,run,kind):
    if (not isinstance(run,str) or not RUN.fullmatch(run) or kind not in KINDS):
        raise ValueError("r4_suggestion_invalid_selection")
    if not schema_ready(db):
        raise ValueError("r4_suggestion_schema_unavailable")
    from bob_r4_ledger import _checked as checked_social
    observed,decision,decision_seal,social_state,_=checked_social(
        db,source_dir,run)
    row=db.execute(
        "SELECT decision_seal,source_post,source_author,title,detail,"
        "seal_sha256,state,created_at,reviewed_at,applied_ref "
        "FROM r4_evidence_suggestions WHERE source_run=? AND kind=?",
        (run,kind)).fetchone()
    if not row:
        raise ValueError("r4_suggestion_not_found")
    stored_seal,post,author,title,detail,digest,state,created,reviewed,ref=row
    original=_payload(observed,decision,decision_seal,kind)
    if original is None or not all((
            stored_seal==decision_seal,post==observed.post_id,
            author==observed.author,title==original["title"],
            detail==original["detail"],isinstance(digest,str),
            SHA.fullmatch(digest),hmac.compare_digest(digest,_seal(original)))):
        raise ValueError("r4_suggestion_evidence_or_seal_changed")
    review=db.execute(
        "SELECT seal_sha256,decision,at,applied_ref "
        "FROM r4_evidence_reviews WHERE source_run=? AND kind=?",
        (run,kind)).fetchone()
    if state=="pending":
        if review is not None or reviewed or ref:
            raise ValueError("r4_pending_suggestion_review_collision")
    elif state in ("approved","rejected"):
        if (review is None or review!=(digest,state,reviewed,ref)
                or (state=="approved" and not ref)
                or (state=="rejected" and ref)):
            raise ValueError("r4_accepted_suggestion_review_tampered")
    else:
        raise ValueError("r4_suggestion_state_invalid")
    return observed,decision,original,digest,state,social_state,ref


def recent(db,source_dir,*,limit=12):
    """Read-only bounded cards, omit any stale/malformed/changed originals."""
    if type(limit) is not int or not 1<=limit<=MAX_LIST or not schema_ready(db):
        return []
    rows=db.execute(
        "SELECT source_run,kind FROM r4_evidence_suggestions "
        "ORDER BY created_at DESC,source_run DESC,kind LIMIT ?",
        (limit,)).fetchall()
    output=[]
    for run,kind in rows:
        try:
            obs,decision,payload,seal,state,social,ref=_checked(
                db,source_dir,run,kind)
            output.append({
                **payload,"seal":seal,"state":state,
                "social_state":social,"applied_ref":ref,
                "remote_following":"not_verified",
                "owner_review_only":True})
        except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):
            continue
    return output


def review(db,source_dir,run,kind,seal,operation,confirmation,
           *,trusted:bool,at:datetime):
    """One exact owner approval, transactional application and audit.

    Memory: create owner-approved low-confidence opinion with fixed source.
    Relationship: stage only verified Scout candidate, NOT add friend/follow.
    """
    if (not trusted or operation not in ("approve","reject") or
            type(at) is not datetime or at.tzinfo is None or
            kind not in KINDS or not isinstance(run,str) or not RUN.fullmatch(run)
            or not isinstance(seal,str) or not SHA.fullmatch(seal)):
        raise ValueError("r4_suggestion_owner_boundary_untrusted")
    phrase=f"{operation.upper()} R4 {kind.upper()} {run}"
    if confirmation!=phrase:
        raise ValueError("r4_suggestion_exact_confirmation_required")
    if not schema_ready(db):
        raise ValueError("r4_suggestion_schema_not_installed")
    db.execute("BEGIN IMMEDIATE")
    try:
        observed,decision,item,current,state,social,_=_checked(
            db,source_dir,run,kind)
        if not hmac.compare_digest(current,seal) or state!="pending":
            raise ValueError("r4_suggestion_stale_or_already_reviewed")
        if operation=="approve" and social=="rejected":
            raise ValueError("r4_parent_social_proposal_rejected")
        applied=""
        if operation=="approve":
            if kind=="memory":
                from bob_memory import create
                fields={
                    "title":item["title"],"content":item["detail"],
                    "category":"opinion","confidence":"low",
                    "source_label":"Owner-approved Bob R4 opinion "+run+
                                   " post "+observed.post_id,
                    "source_url":""}
                applied=create(db,fields)
            else:
                # Existing FM discovery flow independently verifies original
                # Scout author and still requires a fresh public profile and
                # another owner approval before creating a local Friend.
                from bob_friend_discovery import stage
                applied=stage(db,run)
        stamp=at.astimezone(timezone.utc).isoformat()
        status="approved" if operation=="approve" else "rejected"
        change=db.execute(
            "UPDATE r4_evidence_suggestions SET state=?,reviewed_at=?,"
            "applied_ref=? WHERE source_run=? AND kind=? AND "
            "state='pending' AND seal_sha256=?",
            (status,stamp,applied,run,kind,seal))
        if change.rowcount!=1:
            raise ValueError("r4_suggestion_concurrent_update")
        db.execute(
            "INSERT INTO r4_evidence_reviews "
            "(source_run,kind,seal_sha256,decision,at,applied_ref)"
            " VALUES(?,?,?,?,?,?)",
            (run,kind,seal,status,stamp,applied))
        db.commit()
        return {"state":status,"destination":"pm2_owner_memory" if
                kind=="memory" and operation=="approve" else
                "fm_discovery_pending" if kind=="relationship" and
                operation=="approve" else "none",
                "applied_ref":applied,
                "molbook_action_authorized":False}
    except BaseException:
        db.rollback()
        raise
