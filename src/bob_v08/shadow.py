"""R2: isolated Bob shadow tick. Deliberately cannot send Moltbook actions.

One existing OpenClaw main agent makes an opinionated hypothetical decision on
a verified saved Scout selection. Only sanitized metadata enters a separate
SQLite log. No publisher or API functions are imported or invoked.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import tempfile

from .core import Policy, PolicyState, decision_prompt, parse_decision, check
from .evidence import EventStore, latest_observations
from .digest import build_digest

HOME = Path.home()
LEGACY = HOME / ".config/moltbook"
SHADOW = HOME / ".local/state/bob-v08-shadow"
EVENT_DB = SHADOW / "events.sqlite3"
LOCK = SHADOW / "tick.lock"


def _correlation(label: str, run_id: str, post_id: str) -> str:
    return hashlib.sha256((label + ":" + run_id + ":" + post_id).encode()).hexdigest()


def openclaw_decide(prompt: str, session_key: str) -> str:
    """The actual OpenClaw Bob main-agent identity, in its own shadow session."""
    if not session_key.startswith("moltbook-v08-shadow-"):
        raise ValueError("unexpected_shadow_session")
    environment = dict(os.environ)
    environment["PATH"] = (str(HOME / ".openclaw/bin") + ":" +
                           str(HOME / ".openclaw/tools/node/bin") + ":" +
                           environment.get("PATH", ""))
    environment["DOCKER_CONFIG"] = str(HOME / ".docker-openclaw")
    with tempfile.TemporaryDirectory(prefix="bob-v08-shadow-") as directory:
        message = Path(directory) / "prompt.txt"
        message.write_text(prompt, encoding="utf-8")
        message.chmod(0o600)
        try:
            result = subprocess.run(
                ["openclaw", "agent", "--agent", "main",
                 "--session-key", session_key, "--message-file", str(message),
                 "--timeout", "240", "--json"],
                env=environment, capture_output=True, text=True,
                timeout=300, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("shadow_agent_unavailable") from exc
    if result.returncode != 0:
        raise RuntimeError("shadow_agent_cli_failed")
    if not result.stdout or len(result.stdout) > 32768:
        raise ValueError("shadow_agent_envelope_invalid")
    try:
        envelope = json.loads(result.stdout)
    except (TypeError, ValueError):
        raise ValueError("shadow_agent_envelope_invalid") from None
    if not isinstance(envelope, dict) or envelope.get("status") != "ok":
        raise ValueError("shadow_agent_envelope_invalid")
    details = envelope.get("result")
    if not isinstance(details, dict):
        raise ValueError("shadow_agent_envelope_invalid")
    payloads = details.get("payloads")
    if not isinstance(payloads, list) or len(payloads) != 1:
        raise ValueError("shadow_agent_payload_invalid")
    payload = payloads[0]
    if not isinstance(payload, dict):
        raise ValueError("shadow_agent_payload_invalid")
    reply = payload.get("text")
    if not isinstance(reply, str) or not 0 < len(reply) <= 8192:
        raise ValueError("shadow_agent_payload_invalid")
    # The strict five-field source-bound JSON contract remains in parse_decision.
    # Never log the envelope, the reply, stderr or untrusted Moltbook content.
    return reply


def _safe_error_reason(exc: Exception) -> str:
    """Preserve only reviewed categorical errors, never raw model or CLI text."""
    code = str(exc)
    if code in ("shadow_agent_unavailable", "shadow_agent_cli_failed",
                "shadow_agent_envelope_invalid", "shadow_agent_payload_invalid",
                "invalid_model_json", "invalid_model_shape",
                "unverified_model_target", "invalid_model_reason",
                "model_reason_empty", "model_reason_too_long",
                "model_reason_control_chars",
                "skip_must_not_contain_text", "invalid_comment_length",
                "unsafe_comment_text", "copied_untrusted_text"):
        return code
    return "invalid_or_unavailable_model_output"


def run_once(*, legacy: Path = LEGACY, event_db: Path = EVENT_DB,
             model: Callable[[str, str], str] = openclaw_decide,
             policy: Policy | None = None):
    """A single explicit shadow tick; no external Moltbook write path exists.

    R2 should enable a systemd schedule only after versioned install/service
    controls are rehearsed. This function never starts a timer itself.
    """
    if policy is None:
        policy = Policy()
    if not policy.shadow:
        raise ValueError("R2_shadow_mode_required")
    inputs = latest_observations(legacy)
    if not inputs:
        return {"state": "no_verified_saved_sources", "acted": False}
    store = EventStore(event_db)
    with store.open() as db:
        observed = next((item for item in inputs if
                         not store.previously_decided(db, item.run_id, item.post_id)), None)
        if observed is None:
            return {"state": "no_new_verified_sources", "acted": False}
        store.append(db, source_run=observed.run_id, post_id=observed.post_id,
                     kind="observe", state="seen", reason="verified_saved_source",
                     correlation=_correlation("seen", observed.run_id, observed.post_id))
        # Persist provenance before inference in case OpenClaw fails.
        db.commit()
        try:
            raw = model(decision_prompt(observed),
                        "moltbook-v08-shadow-" + observed.run_id)
            action = parse_decision(raw, observed)
        except (ValueError, RuntimeError, TypeError, OSError) as exc:
            store.append(db, source_run=observed.run_id, post_id=observed.post_id,
                         kind="agent_error", state="invalid",
                         reason=_safe_error_reason(exc),
                         correlation=_correlation("error", observed.run_id, observed.post_id))
            return {"state": "model_invalid_or_unavailable", "acted": False,
                    "source_run": observed.run_id}
        store.append(db, source_run=observed.run_id, post_id=observed.post_id,
                     kind="decision", state="decided",
                     reason="bob_decision_" + action.kind, action_type=action.kind,
                     correlation=_correlation("decision", observed.run_id, observed.post_id))
        verdict = check(action, PolicyState(datetime.now(timezone.utc)), policy)
        store.append(db, source_run=observed.run_id, post_id=observed.post_id,
                     kind="policy", state="checked", reason=verdict.reason,
                     action_type=action.kind,
                     correlation=_correlation("policy", observed.run_id, observed.post_id))
        return {
            "state": "shadow_decision",
            "action": action.kind,
            "policy": verdict.disposition,
            "policy_reason": verdict.reason,
            "shadow": True, "acted": False,
            "source_run": observed.run_id, "post_id": observed.post_id
        }


def _locked_once(args):
    SHADOW.mkdir(mode=0o700, parents=True, exist_ok=True)
    if SHADOW.is_symlink() or SHADOW.stat().st_mode & 0o077:
        raise ValueError("unsafe_shadow_directory")
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_once()
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--once", action="store_true",
                         help="run one hypothetical local OpenClaw decision")
    actions.add_argument("--digest", action="store_true",
                         help="print a read-only legacy Moltbook experience digest")
    args = parser.parse_args(argv)
    if os.geteuid() == 0:
        parser.error("do not run the shadow agent as root")
    try:
        if args.digest:
            result = build_digest(LEGACY, LEGACY / "activity-queue.sqlite3")
        else:
            result = _locked_once(args)
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        # No remote payloads, private paths, credentials or model text printed.
        print("BOB SHADOW: refused (" + type(exc).__name__ + ")")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
