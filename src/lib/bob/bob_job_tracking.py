"""Private, best-effort, read-only-to-UI worker stage checkpoints.

These observations are NOT authority to publish, retry, approve, or cancel
jobs. No API key, prompt, post text, exception or credentials are stored.
Single last checkpoint per worker. Atomic replace of mode-0600 JSON.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import tempfile

ROOT = Path.home() / ".config/moltbook/job-progress"
KINDS = frozenset(("scout", "original", "original_publish", "publisher"))
STAGES = frozenset(("queued", "fetching", "validating", "generating", "preflight",
                   "sending", "verifying", "waiting", "completed", "failed",
                   "uncertain", "paused", "idle", "awaiting_verification"))
# Messages are enumerated, never derived from model text, Moltbook API,
# user content, OS exception strings, or arbitrary process output.
NOTES = {
    "queued": "Waiting for worker",
    "fetching": "Collecting public discussions",
    "validating": "Checking output and safety constraints",
    "generating": "Waiting for local agent response",
    "preflight": "Checking target before publication",
    "sending": "Publication attempt started; no blind retry",
    "verifying": "Human verification response pending",
    "waiting": "Waiting for dependencies or posting limits",
    "completed": "Worker step completed",
    "failed": "Worker step failed; inspect logs",
    "uncertain": "Publication result uncertain; do not retry automatically",
    "paused": "Bob is paused",
    "idle": "Worker idle",
    "awaiting_verification": "Human verification required",
}
IDENT = re.compile(r"(?:[0-9a-f]{24}|[0-9]{8}T[0-9]{6}Z|system)\Z", re.I)
ACTIVE = frozenset(("fetching", "validating", "generating", "preflight",
                    "sending", "verifying"))


def checkpoint(kind: str, job_id: str, stage: str, *, root: Path | None = None) -> bool:
    """Noncritical sidecar write: never interfere with worker safety or output."""
    if kind not in KINDS or stage not in STAGES or not isinstance(job_id, str) or not IDENT.fullmatch(job_id):
        return False
    folder = ROOT if root is None else Path(root)
    temp = None
    try:
        if folder.is_symlink():
            return False
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = folder.stat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
            return False
        target = folder / (kind + ".json")
        if target.is_symlink():
            return False
        record = {"worker": kind, "job_id": job_id, "stage": stage,
                  "message": NOTES[stage],
                  "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        raw = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        fd, path = tempfile.mkstemp(prefix=".checkpoint-", dir=folder)
        temp = Path(path)
        with os.fdopen(fd, "wb") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, target)
        temp = None
        return True
    except (OSError, ValueError, TypeError):
        return False
    finally:
        if temp is not None:
            try: temp.unlink(missing_ok=True)
            except OSError: pass


def read_checkpoints(*, root: Path | None = None, at: datetime | None = None):
    """Allowlisted, bounded, owner-private sidecars only. Never execute content."""
    folder = ROOT if root is None else Path(root)
    timestamp = at if at is not None else datetime.now(timezone.utc)
    if folder.is_symlink() or not folder.is_dir():
        return []
    try:
        info = folder.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            return []
    except OSError:
        return []
    result = []
    for kind in sorted(KINDS):
        path = folder / (kind + ".json")
        try:
            if path.is_symlink() or not path.is_file():
                continue
            st = path.stat()
            if st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077 or st.st_size > 2048:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("worker") != kind or data.get("stage") not in STAGES:
                continue
            ident = data.get("job_id")
            if not isinstance(ident, str) or not IDENT.fullmatch(ident):
                continue
            updated = datetime.fromisoformat(data["updated_at"])
            if updated.tzinfo is None:
                continue
            seconds = (timestamp - updated).total_seconds()
            if seconds < -60:
                continue
            stage = data["stage"]
            # An interrupted worker must not appear to run forever. A stale
            # checkpoint means no recent observation, NOT definitive failure.
            stale = stage in ACTIVE and seconds > 360
            result.append({"worker": kind, "job_id": ident,
                           "stage": "unknown" if stale else stage,
                           "message": "No recent worker checkpoint; inspect logs" if stale else NOTES[stage],
                           "updated_at": updated.isoformat(timespec="seconds"),
                           "stale": stale})
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            continue
    return result
