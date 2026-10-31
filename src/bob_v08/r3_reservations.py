"""R3.1 OFFLINE reservation laboratory. No credential, network or live publisher path.

The deliberately isolated SQLite ledger demonstrates atomic idempotency, budget
reservation, rechecks and uncertain outcomes with *simulated* outbound intent.
This is NOT an authorization service, and is NOT installed by the v0.8 manifest.
All callers must supply source-verified observations and freshly read policy.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat

from .core import Action, Observation, Policy, PolicyState, check, parse_decision

SHA = re.compile(r"[a-f0-9]{64}\Z")
TOKEN = re.compile(r"[a-f0-9]{32}\Z")
STATES = frozenset(("reserved", "held", "intent_simulated", "uncertain_simulated"))
LAB_FILENAME = "r3-reservation-lab.sqlite3"
# Never add a network/client/publisher import here. Simulated intent is terminal
# and is not a dispatch request or an approved real publication.
FORMAT = "bob-r3-reservation-lab-v1"


@dataclass(frozen=True)
class Result:
    state: str
    reason: str
    token: str = ""
    simulated: bool = True
    acted: bool = False


def _canonical_action(action: Action, observation: Observation) -> str:
    """Revalidate parsed model output and exact pinned verified-source hashes."""
    if (not isinstance(action, Action) or not isinstance(observation, Observation)
            or not isinstance(observation.snapshot_sha256, str)
            or not SHA.fullmatch(observation.snapshot_sha256)
            or not isinstance(observation.approval_sha256, str)
            or not SHA.fullmatch(observation.approval_sha256)):
        raise ValueError("unverified_source")
    encoded = json.dumps({
        "type": action.kind, "source_run": action.source_run,
        "target_id": action.target_id, "reason": action.reason, "text": action.text,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    try:
        accepted = parse_decision(encoded, observation)
    except (TypeError, ValueError):
        raise ValueError("invalid_reservation_action") from None
    if accepted != action or action.kind != "comment":
        raise ValueError("unsupported_reservation_action")
    encoded = json.dumps({
        "action": json.loads(encoded),
        "snapshot_sha256": observation.snapshot_sha256,
        "approval_sha256": observation.approval_sha256,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _utc(at: datetime) -> datetime:
    if (not isinstance(at, datetime) or at.tzinfo is None
            or at.utcoffset() is None):
        raise ValueError("invalid_reservation_clock")
    return at.astimezone(timezone.utc)


def _stamp(at: datetime) -> str:
    return _utc(at).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _simulate_gate(action: Action, policy: Policy, state: PolicyState, *,
                   auto_enabled: bool, db: sqlite3.Connection,
                   exclude_token: str = "") -> str:
    """Recompute effective counts inside a write transaction.

    Baseline `state` must come from a trusted current legacy-policy loader
    in any future integration, NOT model input. Nothing here can send a POST.
    """
    if not isinstance(policy, Policy) or not isinstance(state, PolicyState):
        return "missing_current_policy"
    if type(auto_enabled) is not bool or not auto_enabled:
        return "legacy_auto_disabled"
    if policy.shadow:
        return "shadow_only"
    spacing = policy.minimum_spacing.get("comment", -1)
    if type(spacing) is not int or spacing < 0:
        return "invalid_spacing"
    if policy.dials.get("comment") != "auto":
        return "comment_not_auto"
    try:
        at = _utc(state.at)
    except ValueError:
        return "invalid_reservation_clock"
    if any(type(v) is not int or v < 0 for v in state.counts.values()):
        return "invalid_baseline_counts"
    counts = dict(state.counts)
    addressed = set(state.addressed)
    last = dict(state.last_action)
    latest = last.get("comment")
    if latest is not None and (not isinstance(latest, datetime)
                               or latest.tzinfo is None):
        return "invalid_baseline_clock"
    if latest is not None:
        latest = _utc(latest)
    rows = db.execute(
        "SELECT token,kind,target_id,created_utc FROM reservations").fetchall()
    for token, kind, target, created in rows:
        if token == exclude_token:
            continue
        try:
            t = datetime.fromisoformat(created.replace("Z", "+00:00"))
            t = _utc(t)
        except (ValueError, TypeError, AttributeError):
            return "invalid_ledger_clock"
        if t > at:
            return "invalid_ledger_clock"
        addressed.add((kind, target))
        if t.date() == at.date():
            counts[kind] = counts.get(kind, 0) + 1
        if kind == "comment" and (latest is None or t > latest):
            latest = t
    if latest is not None:
        last["comment"] = latest
    effective = replace(state, at=at, counts=counts,
                        addressed=frozenset(addressed), last_action=last)
    verdict = check(action, effective, policy)
    return "within_policy" if verdict.disposition == "allow" and not verdict.shadow else verdict.reason


class SimulationLedger:
    """A separate private, disposable SQLite ledger. Not connected to v0.7 DB."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _open(self) -> sqlite3.Connection:
        parent = self.path.parent
        # Deliberately refuse arbitrary or legacy SQLite basenames. R3
        # production schema and dispatch will require an independent review.
        if self.path.name != LAB_FILENAME:
            raise ValueError("untrusted_simulation_path")
        if (parent.is_symlink() or not parent.is_dir()
                or parent.stat().st_mode & 0o077):
            raise ValueError("unsafe_simulation_directory")
        if self.path.is_symlink():
            raise ValueError("unsafe_simulation_database")
        if self.path.exists() and (not self.path.is_file()
                or self.path.stat().st_mode & 0o077):
            raise ValueError("unsafe_simulation_database")
        # Unlike os.umask(), an explicit fd mode is safe across concurrent
        # threads. Existing files and the created file must both be private.
        fd = os.open(self.path, os.O_RDONLY | os.O_CREAT |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("unsafe_simulation_database")
        finally:
            os.close(fd)
        db = sqlite3.connect(self.path, timeout=4, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=4000")
            # BEGIN IMMEDIATE before schema creation serializes first users too.
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS meta(
                         name TEXT PRIMARY KEY, value TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS reservations(
                         token TEXT PRIMARY KEY,
                         kind TEXT NOT NULL,
                         source_run TEXT NOT NULL,
                         target_id TEXT NOT NULL,
                         action_digest TEXT NOT NULL,
                         created_utc TEXT NOT NULL,
                         state TEXT NOT NULL CHECK(state IN (
                           'reserved','held','intent_simulated','uncertain_simulated')),
                         UNIQUE(kind,target_id),
                         UNIQUE(kind,source_run,target_id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS changes(
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         token TEXT NOT NULL,
                         at_utc TEXT NOT NULL,
                         transition TEXT NOT NULL,
                         reason TEXT NOT NULL)""")
            db.execute("INSERT OR IGNORE INTO meta(name,value) VALUES('format',?)",
                       (FORMAT,))
            if db.execute("SELECT value FROM meta WHERE name='format'").fetchone() != (FORMAT,):
                raise ValueError("reservation_schema_mismatch")
            return db
        except BaseException:
            db.rollback()
            db.close()
            raise

    def simulate_reserve(self, action: Action, observed: Observation,
                         policy: Policy, state: PolicyState, *,
                         auto_enabled: bool = False) -> Result:
        """Atomic unique target reservation in an isolated simulation database."""
        digest = _canonical_action(action, observed)
        db = self._open()
        try:
            if db.execute("SELECT 1 FROM reservations WHERE kind=? AND target_id=?",
                          (action.kind, action.target_id)).fetchone():
                db.commit()
                return Result("refused", "duplicate_target")
            reason = _simulate_gate(action, policy, state, auto_enabled=auto_enabled,
                                    db=db)
            if reason != "within_policy":
                db.commit()
                return Result("refused", reason)
            token = secrets.token_hex(16)
            timestamp = _stamp(state.at)
            db.execute(
                "INSERT INTO reservations(token,kind,source_run,target_id,"
                "action_digest,created_utc,state) VALUES(?,?,?,?,?,?,'reserved')",
                (token, action.kind, action.source_run, action.target_id,
                 digest, timestamp))
            db.execute("INSERT INTO changes(token,at_utc,transition,reason)"
                       " VALUES(?,?,?,?)",
                       (token, timestamp, "reserved", "synthetic_policy_pass"))
            db.commit()
            return Result("reserved", "synthetic_policy_pass", token)
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def simulate_pre_send(self, token: str, action: Action, observed: Observation,
                          policy: Policy, state: PolicyState, *,
                          auto_enabled: bool = False) -> Result:
        """Final dry-run recheck; records intent but CANNOT dispatch a request."""
        if not isinstance(token, str) or not TOKEN.fullmatch(token):
            raise ValueError("invalid_reservation_token")
        digest = _canonical_action(action, observed)
        db = self._open()
        try:
            row = db.execute("SELECT kind,source_run,target_id,action_digest,state,"
                             "created_utc FROM reservations WHERE token=?",
                             (token,)).fetchone()
            if row is None:
                db.commit()
                return Result("refused", "reservation_missing")
            kind, run, target, stored, status, original_utc = row
            if status != "reserved":
                db.commit()
                return Result("refused", "reservation_not_pending")
            if (kind, run, target, stored) != (
                    action.kind, action.source_run, action.target_id, digest):
                db.execute("UPDATE reservations SET state='held' WHERE token=?",
                           (token,))
                reason = "reservation_source_changed"
                transition = "held"
            else:
                # A stale/backdated pre-send clock must never authorize an
                # intent just because this reservation is excluded from counts.
                try:
                    earlier = (_utc(state.at) <
                               _utc(datetime.fromisoformat(
                                   original_utc.replace("Z", "+00:00"))))
                except (ValueError, AttributeError, TypeError):
                    earlier = True
                reason = ("invalid_reservation_clock" if earlier else
                          _simulate_gate(action, policy, state,
                                         auto_enabled=auto_enabled, db=db,
                                         exclude_token=token))
                transition = "intent_simulated" if reason == "within_policy" else "held"
                db.execute("UPDATE reservations SET state=? WHERE token=?",
                           (transition, token))
            now = _stamp(state.at)
            db.execute("INSERT INTO changes(token,at_utc,transition,reason)"
                       " VALUES(?,?,?,?)", (token, now, transition, reason))
            db.commit()
            return Result(transition, reason, token)
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def simulate_uncertain(self, token: str, at: datetime) -> Result:
        """A crash/ambiguous outcome remains locked; never retry the target."""
        if not isinstance(token, str) or not TOKEN.fullmatch(token):
            raise ValueError("invalid_reservation_token")
        stamp = _stamp(at)
        db = self._open()
        try:
            change = db.execute("UPDATE reservations SET state='uncertain_simulated'"
                                " WHERE token=? AND state='intent_simulated'",
                                (token,))
            if change.rowcount != 1:
                db.commit()
                return Result("refused", "uncertain_transition_denied")
            db.execute("INSERT INTO changes(token,at_utc,transition,reason)"
                       " VALUES(?,?,?,?)",
                       (token, stamp, "uncertain_simulated", "synthetic_unknown_outcome"))
            db.commit()
            return Result("uncertain_simulated", "synthetic_unknown_outcome", token)
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
