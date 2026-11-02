#!/usr/bin/env python3
"""Single R4 OpenClaw contract diagnostic; NO R4/social DB writes or publisher.

This intentionally makes ONE existing OpenClaw main-agent inference in a
distinct diagnostic shadow session. OpenClaw itself may save that session.
The signed installed R4 bridge, model transport, source and owner modes are
verified before inference; only allowlisted reasons reach stdout. No model
text, Scout content, credentials, shell stderr, private paths or SQL data are
printed. Does not insert an R4 decision, queue, review, or public API request.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import pwd
import secrets
import sqlite3
import stat
import sys

PREVIOUS_RUN="20261102T042747Z"  # Historical refused source; NEVER replay it.
RELEASE="v0.8.0-r4propose1"
SESSION_PREFIX="moltbook-v08-shadow-r4-diagnostic-"
FORMAT_PREFIX="moltbook-v08-shadow-r4-format-"
EXPECTED_FIELDS=("type","source_run","target_id","reason",
                 "text","title","submolt","parent_id")
ALLOWED_ERRORS=frozenset((
    # The existing verified OpenClaw transport's error identifiers.
    "unexpected_shadow_session","shadow_agent_unavailable",
    "shadow_agent_cli_failed","shadow_agent_envelope_invalid",
    "shadow_agent_payload_invalid",
    # The existing installed R4 prompt/decision parser's errors.
    "r4_unreviewed_owner_modes","r4_no_permitted_social_actions",
    "r4_invalid_model_or_clock","r4_all_owner_actions_off",
    "r4_untrusted_decision_envelope","r4_invalid_decision_json",
    "r4_invalid_exact_eight_field_schema","r4_unknown_action_type",
    "r4_unverified_source_shape","r4_invalid_source_time",
    "r4_stale_source","r4_changed_source_id",
    "r4_invalid_saved_post_id","r4_invalid_skip_fields",
    "r4_skip_reason_too_long","r4_invalid_reason",
    "r4_model_changed_post_target","r4_model_changed_verified_author",
    "r4_model_original_target_invalid","r4_invalid_draft_body",
    "r4_noncontent_action_has_body",
    "r4_original_post_unreviewed_destination",
    "r4_nonpost_metadata_forbidden",
    "r4_reply_parent_not_independently_verified",
    "r4_remote_following_not_verified",
    "r4_insufficient_repeat_author_evidence",
    "r4_model_selected_disabled_action",
))


def safe_error(exc:Exception)->str:
    """No arbitrary model text, paths, tokens or subprocess stderr."""
    candidate=str(exc)
    return candidate if candidate in ALLOWED_ERRORS else "unclassified_error"


def sanitized_shape(raw)->dict:
    """Describe format without exposing ANY returned field names or values.

    Only names from our own fixed eight-field allowlist appear in output.
    Arbitrary model keys, text, prompts and JSON values are never echoed.
    """
    shape={"top_level":"unavailable","missing_expected":[],
           "non_string_expected":[],"extra_field_count":0}
    if type(raw) is not str or not 0<len(raw.encode("utf-8"))<=8192:
        return shape
    try:
        value=json.loads(raw)
    except (ValueError,TypeError):
        shape["top_level"]="invalid_json"
        return shape
    if type(value) is not dict:
        shape["top_level"]=("array" if type(value) is list else "other")
        return shape
    shape["top_level"]="object"
    shape["missing_expected"]=[k for k in EXPECTED_FIELDS if k not in value]
    shape["non_string_expected"]=[
        k for k in EXPECTED_FIELDS if k in value and type(value[k]) is not str
    ]
    shape["extra_field_count"]=min(
        32,sum(1 for k in value if k not in EXPECTED_FIELDS))
    return shape


def _format_test_prompt(original:str,observed)->str:
    """Trusted output-only instruction, appended AFTER untrusted source."""
    from bob_r4_decision import exact_example
    if type(original) is not str:
        raise ValueError("r4_untrusted_decision_envelope")
    # Supports BOTH installed signed releases: original r4propose1 prompt
    # ends at the untrusted boundary; r4format1 adds its own trusted JSON
    # reminder after that boundary. Never accept an arbitrary alternative
    # prompt string or allow untrusted content to become trusted instructions.
    old_boundary="\nEND_UNTRUSTED_MOLTBOOK_JSON\n"
    new_boundary=old_boundary+"\nTRUSTED OUTPUT CONTRACT:"
    if not (original.endswith(old_boundary)
            or (new_boundary in original
                and original.endswith("\nFINAL ANSWER: SINGLE JSON OBJECT ONLY.\n"))):
        raise ValueError("r4_untrusted_decision_envelope")
    return original+(
        "\nTRUSTED OUTPUT CONTRACT (this is NOT permission to take action): "
        "Return EXACTLY ONE JSON object, with these eight keys and NO others: "
        "type, source_run, target_id, reason, text, title, submolt, parent_id. "
        "ALL eight values must be JSON strings, including empty strings. "
        "Never use null, numbers, lists or nested objects for any field. "
        "Do not omit empty fields. Do not wrap the JSON in markdown fences. "
        "Do not write an explanation outside the JSON. "
        "Use skip when no permitted action is clearly justified. "
        "A correct complete SKIP example using this sealed source is: "+
        exact_example(observed)+". "
        "If proposing a non-skip action, keep all eight fields and the exact "
        "source_run; follow the action-specific rules above.\n"
    )


def _session_key(session:str,run:str,*,production:bool)->str:
    """Only use the R4 bridge's exact source-specific session identity."""
    expected="moltbook-v08-shadow-r4-proposal-"+run
    if (type(run) is not str or type(session) is not str or
            type(production) is not bool or session!=expected):
        raise ValueError("unexpected_shadow_session")
    return session if production else SESSION_PREFIX+run


def _ledger_owner(db, run:str)->str:
    """Which original ledger has the historical source (no row content)."""
    found=[]
    for name,table,column in (
        ("r4","r4_social_decisions","source_run"),
        ("r3","r3_proposals","source_run"),
        ("publisher","publish_jobs","run_id"),
    ):
        if db.execute("SELECT 1 FROM "+table+" WHERE "+column+"=?",
                      (run,)).fetchone():
            found.append(name)
    return found[0] if len(found)==1 else (
        "multiple" if found else "none")


def _next_available(db, choices, now:datetime):
    """Exact producer source order, age window, and prior-consumption gates."""
    from bob_r4_decision import SOURCE_AGE
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("r4_invalid_model_or_clock")
    if not isinstance(choices,(list,tuple)) or len(choices)>20:
        raise ValueError("r4_untrusted_decision_envelope")
    for item in choices:
        try:
            stamp=datetime.strptime(item.run_id,"%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc)
            age=now.astimezone(timezone.utc)-stamp
            if not timedelta(0)<=age<=SOURCE_AGE:
                continue
            if _ledger_owner(db,item.run_id)!="none":
                continue
            return item
        except (ValueError,TypeError,AttributeError,sqlite3.Error):
            continue
    return None


def result(*,stage:str,reason:str,called:bool=False,
           verified_kind:str="none",source_run:str="",
           previous_owner:str="unknown",
           session_scope:str="isolated",response_shape=None)->dict:
    if stage not in ("host","source","controls","transport",
                     "contract","valid_private_decision"):
        stage="host"
    if reason not in ALLOWED_ERRORS and reason not in (
            "ok","source_not_recent","source_already_used",
            "owner_off_or_paused","signed_install_not_verified",
            "saved_feed_not_verified","private_database_not_verified",
            "invalid_account","unclassified_error",
            "no_fresh_r4_source"):
        reason="unclassified_error"
    return {
        "format":"r4-agent-contract-diagnostic-v1",
        "source_run":source_run if isinstance(source_run,str) and
            len(source_run)==16 and source_run[:8].isdigit() and
            source_run[8]=="T" and source_run[9:15].isdigit() and
            source_run[15]=="Z" else "",
        "historical_source_run":PREVIOUS_RUN,
        "historical_source_owner":previous_owner if previous_owner in
            ("r3","r4","publisher","multiple","none","unknown") else "unknown",
        "stage":stage,
        "reason":reason,
        "verified_action_kind":verified_kind if
            verified_kind in ("none","skip","upvote","comment","post","follow")
            else "none",
        "openclaw_called":called,
        "requested_session_scope":session_scope if session_scope in
            ("isolated","production","fresh_format") else "unverified",
        "isolated_agent_session":called and session_scope in
            ("isolated","fresh_format"),
        "fresh_format_experiment":session_scope=="fresh_format",
        "response_shape":response_shape if session_scope=="fresh_format"
            and isinstance(response_shape,dict) else None,
        "production_session_touched":called and session_scope=="production",
        "r4_decision_recorded":False,
        "r4_proposal_queued":False,
        "public_social_dispatch_authorized":False,
        "publisher_or_service_changed_by_probe":False,
        "production_database_writes_by_probe":False,
    }


def diagnose(*,production_session:bool=False,fresh_format:bool=False)->dict:
    """Optional exact source-session trace; never records a social action.

    An explicit owner-facing command and terminal confirmation are required
    before using the live source-specific OpenClaw session. This leaves the
    private database query-only, but OpenClaw itself persists a session turn.
    """
    if (type(production_session) is not bool or type(fresh_format) is not bool
            or production_session and fresh_format):
        raise ValueError("r4_unreviewed_session_diagnostic")
    called=False
    stage="host"
    run=""
    prior_owner="unknown"
    scope=("production" if production_session else
           "fresh_format" if fresh_format else "isolated")
    def emit(**fields):
        return result(session_scope=scope,**fields)
    try:
        home=Path.home()
        uid=os.geteuid()
        if uid==0 or pwd.getpwuid(uid).pw_dir!=str(home):
            return emit(stage="host",reason="invalid_account")
        bindir=home/".local/bin"
        # Never load R4 code from a mutable Git checkout.
        if str(bindir) not in sys.path:
            sys.path.insert(0,str(bindir))
        import bob_r4_installed_gate as installed_gate
        from bob_r313d_package import load_verified
        if not installed_gate.verify():
            return emit(stage="host",reason="signed_install_not_verified")
        registry=json.loads((home/".local/state/bob-updater/installed.json")
                            .read_text(encoding="utf-8"))
        if registry.get("release")!=RELEASE or (
                load_verified()!="verified_registry_archive"):
            return emit(stage="host",reason="signed_install_not_verified")

        from bob_publish_common import DATA,DB
        from bob_r313d_owner import trusted_manager_boundary
        from bob_r4_controls import read_modes,pause_state
        from bob_r4_ledger import schema_ready,author_count
        from bob_v08.evidence import latest_observations
        from bob_v08.shadow import openclaw_decide
        from bob_r4_agent import decide,AVAILABLE

        stage="source"
        if (DATA.is_symlink() or not DATA.is_dir()
                or DATA.stat().st_uid!=uid
                or DATA.stat().st_mode & 0o077):
            return emit(stage="source",reason="saved_feed_not_verified")
        now=datetime.now(timezone.utc)
        if DB.is_symlink() or not stat.S_ISREG(DB.stat().st_mode):
            return emit(stage="host",reason="private_database_not_verified")
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro",
                                     uri=True,timeout=5)) as db:
            db.execute("PRAGMA query_only=ON")
            if not trusted_manager_boundary(db) or not schema_ready(db):
                return emit(stage="host",reason="private_database_not_verified")
            prior_owner=_ledger_owner(db,PREVIOUS_RUN)
            stage="controls"
            modes=read_modes(db)
            if pause_state(db) or not any(
                    modes[a]=="propose" for a in AVAILABLE):
                return emit(stage="controls",reason="owner_off_or_paused",
                              previous_owner=prior_owner)
            stage="source"
            # Same bounded, sealed 100-file scan / 20-result selection as
            # the installed producer. Never choose the previous run merely
            # because it was used during an earlier refusal.
            choices=latest_observations(DATA,max_scan=100,limit=20)
            observed=_next_available(db,choices,now)
            if observed is None:
                return emit(stage="source",reason="no_fresh_r4_source",
                              previous_owner=prior_owner)
            run=observed.run_id
            repeats=author_count(DATA,observed)

        # Existing signed agent bridge invokes the original OpenClaw transport,
        # then applies the unchanged strict exact-eight-field parser and
        # action/target/age restrictions. This script never calls record().
        stage="transport"
        transport_completed=False
        raw_reply=None
        def model(prompt,session):
            nonlocal called,transport_completed,raw_reply
            # Default probe uses its isolated diagnostic session. Only
            # explicit --production-session-once with a second owner-typed
            # confirmation reuses the SAME source-specific session key as
            # the signed normal R4 worker. No bypass of the real parser.
            key=_session_key(session,run,production=production_session)
            if fresh_format:
                # The experiment must not reuse or reset any production
                # session. A fresh unpredictable shadow key isolates this
                # single test turn from earlier model-format failures.
                key=FORMAT_PREFIX+run+"-"+secrets.token_hex(8)
                prompt=_format_test_prompt(prompt,observed)
            called=True
            raw_reply=openclaw_decide(prompt,key)
            transport_completed=True
            return raw_reply
        try:
            decision=decide(observed,modes=modes,model=model,now=now,
                            author_observations=repeats)
        except (OSError,ValueError,RuntimeError,TypeError) as exc:
            return emit(stage="contract" if transport_completed else "transport",
                          reason=safe_error(exc),called=called,
                          source_run=run,previous_owner=prior_owner,
                          response_shape=sanitized_shape(raw_reply)
                              if fresh_format and transport_completed else None)
        return emit(stage="valid_private_decision",reason="ok",
                      called=called,verified_kind=decision.kind,
                      source_run=run,previous_owner=prior_owner,
                      response_shape=sanitized_shape(raw_reply)
                          if fresh_format else None)
    except (OSError,ValueError,TypeError,RuntimeError,ImportError,
            KeyError,AttributeError,sqlite3.Error,UnicodeError) as exc:
        return emit(stage=stage,reason=safe_error(exc),called=called,
                      source_run=run,previous_owner=prior_owner)


def main(argv=None)->int:
    args=sys.argv[1:] if argv is None else argv
    if args not in (["--once"],["--production-session-once"],
                    ["--fresh-format-once"]):
        print("Usage: python3 scripts/report_r4_agent_contract.py "
              "--once | --production-session-once | --fresh-format-once "
              "(one local OpenClaw main-agent call; no R4 record or social send)")
        return 2
    production=args==["--production-session-once"]
    format_test=args==["--fresh-format-once"]
    if production or format_test:
        # A normal --once can be used without prompting; sharing the exact
        # production R4 OpenClaw session is an additional explicit action.
        # No CLI flags, environment values or nonterminal input may bypass.
        if not sys.stdin.isatty():
            print("R4 SESSION TRACE: refused (terminal confirmation required)")
            return 1
        try:
            phrase=("TRACE R4 SESSION" if production
                    else "TEST R4 JSON FORMAT")
            approval=input(
                ("Add ONE diagnostic turn to existing production R4 session. "
                 if production else
                 "Call Bob ONCE in a fresh private test session with "
                 "a stronger JSON-only format prompt. ")+
                "No R4 database or social writes. Type "+phrase+": ")
        except (EOFError,KeyboardInterrupt):
            print("R4 SESSION TRACE: refused (confirmation unavailable)")
            return 1
        if approval!=phrase:
            print("R4 SESSION TRACE: refused (confirmation not granted)")
            return 1
    report=diagnose(production_session=production,fresh_format=format_test)
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    return 0 if report["stage"]=="valid_private_decision" else 1


if __name__=="__main__":
    raise SystemExit(main())
