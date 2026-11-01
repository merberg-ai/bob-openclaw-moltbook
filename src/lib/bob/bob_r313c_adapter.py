"""R3.13c prospective REAL single-publisher R3 branch, COMPILED OFF.

Only src/bin/bob-moltbook-publisher imports this adapter. Real network calls
would reuse ITS existing api()/api_key(), not create a second credential owner.
No env flag, persisted owner bit, CLI flag, or synthetic fixture can turn it
on. A later reviewed versioned release must explicitly change the source
constant after on-host schema/owner UI/rollback authorization.

All R3.13c tests use fake in-memory transport in marked private fixtures.
"""
from __future__ import annotations

import os
from pathlib import Path
import pwd
import sqlite3

from bob_publish_common import DATA, UUID
from bob_r312_adapter import R312_REAL_DISPATCH

R313C_REAL_DISPATCH = False
R313C_SOURCE_VERSION = "r313c-exact-manual-canary-v1"


R3_EXACT_CANARY_COMPILED = True  # one source-locked public action only


def production_dispatch_enabled() -> bool:
    """No global R3 dispatch; only a compiled PIN plus explicit owner arm."""
    if not R3_EXACT_CANARY_COMPILED:
        return False
    try:
        from bob_r3_canary_lock import marker_valid
        from datetime import datetime, timezone
        return marker_valid(now=datetime.now(timezone.utc))
    except (OSError,ValueError,TypeError,ImportError):
        return False


def _trusted_single_publisher_db(db: sqlite3.Connection) -> bool:
    """Fixed installed queue and private source and pause paths, never args."""
    from bob_v08.r313a_private_migration import _private
    account = Path.home()
    if os.geteuid() == 0 or pwd.getpwuid(os.geteuid()).pw_dir != str(account):
        return False
    # The private leaf checks alone are insufficient if HOME/.config
    # ancestors are symlinked or writable by a different local process.
    import stat
    for path in (account, account / ".config"):
        try:
            info = path.lstat()
            if (not stat.S_ISDIR(info.st_mode)
                    or info.st_uid != os.geteuid() or info.st_mode & 0o022):
                return False
        except OSError:
            return False
    if not all(_private(path, directory=True, uid=os.geteuid()) for path in (
            DATA, account / ".config/bob-system")):
        return False
    rows = db.execute("PRAGMA database_list").fetchall()
    mains = [row for row in rows if row[1] == "main"]
    if len(mains) != 1 or any(row[1] not in ("main", "temp")
                              or row[1] == "temp" and row[2] for row in rows):
        return False
    path = DATA / "activity-queue.sqlite3"
    if (Path(mains[0][2]) != path
            or not _private(path, directory=False, uid=os.geteuid())):
        return False
    # Exact future versioned schema, not R3.5's proposal-only lab data.
    version = db.execute(
        "SELECT value FROM r313c_schema_meta WHERE name='version'").fetchone()
    return version == ("r313c-action-v1",)


def maybe_r3_publisher_step(db, *, api_call, credential_loader):
    """Return None for legacy branch; compiled-Off cannot read R3 or send.

    The prospective reviewed activation must still get a separate owner
    release and use exact fixed-host GET, fresh source/owner/friend/pause
    checks, durable intent, final barrier, and no-retry ambiguous handling.
    """
    if not production_dispatch_enabled():
        return None
    # Unreachable in current source candidate; future release review must
    # attest installed source/hash, full R3 additive schema and owner UI.
    try:
        # Verify the exact VERSIONED local R3 archive and installed registry
        # before importing any bob_v08 module. _trusted_single_publisher_db
        # imports shared R3 schema helpers, so even that check must follow
        # the verified source-path setup. No extra publisher or credential
        # owner is created. This branch remains compiled hard Off.
        from bob_r313d_package import load_verified
        if load_verified() != "verified_registry_archive":
            return "R3 installed archive unverified; no send"
        if not _trusted_single_publisher_db(db):
            return "R3 candidate host boundary refused; no send"
        from bob_v08.r313c_candidate import (
            candidate_step, recover_inflight, _head,
        )
        from bob_v08.r39_publisher_review import public_get_post
        from datetime import datetime, timezone
        recovered = recover_inflight(db)
        if recovered:
            return "R3 interrupted attempted send marked uncertain; no replay"
        head = _head(db)
        if head is None:
            return None  # Legacy manual/auto head remains authoritative.
        from bob_r3_canary_lock import (
            installed_canary_ready, still_pinned_for_send,
        )
        if not installed_canary_ready(
                db, DATA, head, now=datetime.now(timezone.utc)):
            return "R3 exact public canary source pin Off; no send"
        pause = Path.home() / ".config/bob-system/paused"

        def exact_publisher_post(post_id, text):
            # Late expiry/target check after durable intent and final barrier.
            # Refusal leaves an uncertain attempt, NEVER a requeued retry.
            if not still_pinned_for_send(
                    head, post_id, datetime.now(timezone.utc)):
                raise ValueError("r3_canary_expired_or_target_changed")
            if not isinstance(post_id, str) or not UUID.fullmatch(post_id):
                raise ValueError("invalid_single_publisher_target")
            # Credential stays in the EXISTING publisher, never passed to
            # the model, dashboard, file or second network worker.
            return api_call("POST", "/posts/" + post_id + "/comments",
                            {"content": text}, key=credential_loader())

        outcome = candidate_step(
            db, DATA, pause,
            clock=lambda: datetime.now(timezone.utc),
            public_get=public_get_post,
            post_comment=exact_publisher_post,
            exact_canary_run=head)
        if outcome.status == "not_selected":
            return None  # Existing legacy Scout job remains authoritative.
        return "R3 candidate outcome: " + outcome.status
    except (OSError, sqlite3.Error, ValueError, TypeError, ImportError, KeyError):
        return "R3 candidate fail-closed; no send"
