"""R3.7 OFFLINE trusted-publisher pre-send gate rehearsal.

A fixed-source, single-ledger dry run. The host-owned GET and monotonic clock
are *injected test fixtures*, never model-provided approval or network clients.
Every outcome has acted=False; this module cannot send or load credentials.

Production integration MUST separately authenticate owner consent, source
storage and HTTPS GET, and bind the real publisher's final CAS before a POST.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .core import Action, Policy
from .r3_cutover_rehearsal import verified_source, simulated_pause_state
from .r3_unified import UnifiedLab, Proof
from .r36_admission_contract import classify_draft

# Exact existing v0.7 policy reader, never a second approximation of rate limits.
from .r3_unified import legacy_allowed
from bob_activity_limits import read_limits


@dataclass(frozen=True)
class GateResult:
    state: str
    reason: str
    simulated: bool = True
    acted: bool = False
    dispatch_authorized: bool = False


def _utc(at):
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("invalid_clock")
    return at.astimezone(timezone.utc)


def _read_friends(db, root: Path, action: Action, obs) -> str:
    """Recheck the *actual verified feed* and private friend table, fail closed."""
    file = Path(root) / ("scout-feed-" + action.source_run + ".json")
    try:
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 512 * 1024:
            return "friend_feed_unavailable"
        raw = file.read_bytes()
        if hashlib.sha256(raw).hexdigest() != obs.snapshot_sha256:
            return "friend_feed_changed"
        feed = json.loads(raw)
        if not isinstance(feed, dict) or feed.get("friend_focus") is True:
            return "friend_focused_source"
        posts = feed.get("posts")
        if not isinstance(posts, list) or any(
                isinstance(p, dict) and p.get("from_friend") is True for p in posts):
            return "friend_tagged_batch"
        selected = next((p for p in posts if isinstance(p, dict)
                         and p.get("id") == action.target_id), None)
        if not isinstance(selected, dict):
            return "friend_target_unverified"
        author = selected.get("author")
        if not isinstance(author, str) or not author.strip():
            return "friend_author_missing"
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                      "AND name='bob_friends'").fetchone() is None:
            return "friend_table_missing"
        if db.execute("SELECT 1 FROM bob_friends WHERE handle_key=?",
                      (author.casefold(),)).fetchone():
            return "friend_target_protected"
        return "clear"
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return "friend_guard_unavailable"


def _one_pass(lab: UnifiedLab, source_dir: Path, action: Action, mode: str, at,
              pause_marker: Path):
    """Re-read source/owner/queue/friend/limits at each boundary.

    The caller cannot supply an authorization boolean. In this laboratory the
    database is a MARKED synthetic fixture: no production path can be opened.
    """
    if simulated_pause_state(pause_marker):
        return "paused_or_untrusted_marker", None
    try:
        obs, pin = verified_source(source_dir, action)
    except (OSError, ValueError, TypeError):
        return "saved_source_unverified", None
    db = lab._open()
    try:
        origin = classify_draft(db, source_dir, action)
        if origin.origin != "r3_bob":
            return "not_a_new_sealed_bob_draft", None
        job = db.execute(
            "SELECT mode,state,attempted_at FROM publish_jobs WHERE run_id=?",
            (action.source_run,)).fetchone()
        if job != (mode, "queued", None):
            return "job_not_pending", None
        owner = db.execute(
            "SELECT name,value FROM publish_settings WHERE name IN "
            "('auto_enabled','r3_auto_enabled','r3_comment_dial','r3_auto_since')"
        ).fetchall()
        settings = dict(owner)
        dial = settings.get("r3_comment_dial", "off")
        if dial not in ("auto", "propose"):
            return "owner_dial_off", None
        if mode == "auto":
            if dial != "auto" or settings.get("auto_enabled") != "1" or (
                    settings.get("r3_auto_enabled") != "1"):
                return "separate_auto_consent_missing", None
            try:
                since = _utc(datetime.fromisoformat(
                    settings["r3_auto_since"].replace("Z", "+00:00")))
                source_time = datetime.strptime(
                    action.source_run, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except (ValueError, KeyError, AttributeError, TypeError):
                return "auto_since_unverified", None
            if source_time <= since:
                return "old_source_before_opt_in", None
            if db.execute("SELECT 1 FROM decisions WHERE run_id=?",
                          (action.source_run,)).fetchone():
                return "legacy_owner_override", None
            friend = _read_friends(db, source_dir, action, obs)
            if friend != "clear":
                return friend, None
        else:
            from .r3_unified import _validated
            seal, _ = _validated(action, obs)
            approved = db.execute(
                "SELECT seal_sha256,decision FROM r3_owner_approvals "
                "WHERE source_run=?", (action.source_run,)).fetchone()
            if approved != (seal, "approved"):
                return "specific_bob_draft_not_approved", None
        try:
            limits = read_limits(db)
            eligible, _ = legacy_allowed(db, "comment", mode=mode, at=_utc(at))
        except (ValueError, TypeError, sqlite3.Error):
            return "legacy_limits_unavailable", None
        if not eligible:
            return "legacy_budget_or_spacing", None
        if db.execute("SELECT 1 FROM publish_jobs WHERE post_id=? "
                      "AND run_id<>? AND (attempted_at IS NOT NULL OR state IN "
                      "('sending','uncertain','published','verified_unconfirmed',"
                      "'awaiting_verification','verifying','verification_expired',"
                      "'verification_failed')) LIMIT 1",
                      (action.target_id, action.source_run)).fetchone():
            return "duplicate_or_uncertain_target", None
        head = db.execute(
            "SELECT run_id FROM publish_jobs WHERE state='queued' "
            "ORDER BY CASE WHEN mode='manual' THEN 0 ELSE 1 END,"
            "created_at ASC,run_id ASC LIMIT 1").fetchone()
        if head != (action.source_run,):
            return "manual_first_queue_priority", None
        # Synthetic policy is DERIVED from persisted owner settings and
        # validated v0.7 limits, never supplied by model, API or dashboard.
        policy = replace(
            Policy(), shadow=False, dials={"comment": dial},
            budgets={"comment": limits["comment_daily"]},
            minimum_spacing={"comment": limits["comment_gap_minutes"]})
        return "ready_for_synthetic_recheck", (pin, policy)
    except (sqlite3.Error, ValueError, TypeError, KeyError):
        return "host_boundary_unavailable", None
    finally:
        db.rollback()
        db.close()


def _get_matches(response, action: Action, obs) -> bool:
    """Require an exact post and stable author; missing identity is NOT success."""
    if not isinstance(response, dict) or response.get("success") is False:
        return False
    data = response.get("data", response)
    if not isinstance(data, dict):
        return False
    post = data.get("post", data)
    if not isinstance(post, dict) or post.get("id") != action.target_id:
        return False
    if post.get("deleted") is True or post.get("is_deleted") is True:
        return False
    author = post.get("author")
    if isinstance(author, dict):
        author = author.get("name", author.get("username"))
    return isinstance(author, str) and author.casefold() == obs.author.casefold()


def rehearse_trusted_gate(lab: UnifiedLab, source_dir: Path, action: Action, *,
                          mode: str, pause_marker: Path,
                          get_post, clock) -> GateResult:
    """The only positive path is a *synthetic* attempted_at in the lab DB.

    This function neither generates a request nor obtains credentials. The
    trusted test harness owns get_post and clock, not Bob's model output.
    Two independently opened transactions bracket the simulated HTTP GET so
    no SQLite writer lock is held across a network-like operation.
    """
    if not isinstance(lab, UnifiedLab) or mode not in ("manual", "auto"):
        return GateResult("refused", "invalid_synthetic_publisher")
    if not callable(get_post) or not callable(clock):
        return GateResult("refused", "host_preflight_adapter_missing")
    try:
        before = _utc(clock())
    except (ValueError, TypeError):
        return GateResult("refused", "untrusted_clock")
    first, state = _one_pass(lab, source_dir, action, mode, before, pause_marker)
    if state is None:
        return GateResult("refused", first)
    pinned, _ = state
    try:
        obs, observed_pin = verified_source(source_dir, action, pinned=pinned)
        if observed_pin != pinned:
            return GateResult("refused", "source_changed_before_get")
        response = get_post(action.target_id)
        after = _utc(clock())
    except (OSError, ValueError, TypeError, KeyError, TimeoutError):
        return GateResult("refused", "get_or_source_unverified")
    if after < before or after - before > timedelta(minutes=2):
        return GateResult("refused", "get_stale_or_clock_changed")
    if not _get_matches(response, action, obs):
        return GateResult("refused", "get_target_author_unverified")
    second, second_state = _one_pass(lab, source_dir, action, mode, after, pause_marker)
    if second_state is None:
        return GateResult("refused", "recheck_" + second)
    if second_state[0] != pinned:
        return GateResult("refused", "source_pin_changed_during_get")
    # This is a simulation boundary only. The real publisher's final pause
    # and consent rechecks, durable intent and POST do not exist here.
    from .r3_unified import Proof
    outcome = lab.simulated_pre_send(
        action, obs, mode=mode, at=after, policy=second_state[1],
        paused=simulated_pause_state(pause_marker),
        proof=Proof(action.target_id, after, "clear"))
    return GateResult(
        outcome.state, outcome.reason, simulated=True, acted=False,
        dispatch_authorized=False)
