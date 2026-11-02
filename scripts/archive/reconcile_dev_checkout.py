#!/usr/bin/env python3
"""Reconcile a clean local reviewed-source commit with identical GitHub source.

DO NOT use on a dirty worktree. Run from repository root only *after* git fetch.
Never touches installed Bob scripts, user home configs, systemd or SQLite.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
import sys

FEATURE = "feature/v0.7.0-host-inventory"
LOCAL_REVIEWED = "28073f1"
REMOTE_REVIEWED = "f3db4b445f379f997f950976576c6a5289e11774"
BACKUP = "backup/v070-reviewed-local-28073f1"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], text=True, capture_output=True,
                          timeout=15, check=check)


def validate() -> tuple[str, str]:
    if git("rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        raise ValueError("Not in a Git worktree")
    root = Path(git("rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if root != Path.cwd().resolve():
        raise ValueError("Run at repository root, not another directory")
    if root.name != "bob-v070-inventory":
        raise ValueError("Unexpected repository checkout")
    if git("branch", "--show-current").stdout.strip() != FEATURE:
        raise ValueError("Unexpected current branch")
    if git("status", "--porcelain", "--untracked-files=all").stdout.strip():
        raise ValueError("Working tree has local changes; refusing reset")
    local = git("rev-parse", "HEAD").stdout.strip()
    if not local.startswith(LOCAL_REVIEWED) or len(local) != 40:
        raise ValueError("Local commit differs from reviewed commit; refusing reset")
    remote = git("rev-parse", f"refs/remotes/origin/{FEATURE}").stdout.strip()
    if not remote or len(remote) != 40:
        raise ValueError("Remote branch not fetched")
    reviewed = git("rev-parse", REMOTE_REVIEWED).stdout.strip()
    if reviewed != REMOTE_REVIEWED:
        raise ValueError("Reviewed remote commit not present")
    if git("diff", "--quiet", "HEAD", REMOTE_REVIEWED, check=False).returncode != 0:
        raise ValueError("Source trees differ; refusing reset")
    if git("merge-base", "--is-ancestor", REMOTE_REVIEWED, remote,
           check=False).returncode != 0:
        raise ValueError("Origin branch does not contain reviewed remote commit")
    existing = git("rev-parse", "--verify", "--quiet",
                   f"refs/heads/{BACKUP}", check=False).stdout.strip()
    if existing and existing != local:
        raise ValueError("Backup branch exists but points elsewhere")
    return local, remote


def main() -> int:
    try:
        local, remote = validate()
        git("branch", "-f", BACKUP, local)
        # All checks above must pass before any ref rewrite.
        git("reset", "--hard", remote)
        if git("status", "--porcelain", "--untracked-files=all").stdout.strip():
            raise RuntimeError("Checkout not clean after reset")
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
        print("CHECKOUT SYNC REFUSED:", type(exc).__name__,
              "(no live application files modified)", file=sys.stderr)
        return 1
    print("Development checkout synchronized with GitHub feature branch.")
    print("Previous local reviewed commit preserved as", BACKUP)
    print("Development HEAD:", remote[:12])
    print("Clean checkout; no live service, configuration, or database changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
