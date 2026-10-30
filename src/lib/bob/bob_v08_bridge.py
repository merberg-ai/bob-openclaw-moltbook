"""R2 read-only adapter for the authenticated legacy Activity Manager.

This module never serves HTTP by itself and must only be called after the
existing Activity Manager's authentication checks. Loading a reviewed zip does
not start the agent, install services or touch publisher credentials.
"""
from __future__ import annotations

from pathlib import Path
import sys

PACKAGE = Path.home() / ".local/bin/bob_v08_package.pyz"
if (PACKAGE.is_symlink() or not PACKAGE.is_file()
        or not 0 < PACKAGE.stat().st_size <= 512 * 1024):
    raise RuntimeError("v0.8 shadow archive not installed")
sys.path.insert(0, str(PACKAGE))

from bob_v08.inspect import render_now, render_inbox


def now_page(wrap):
    return render_now(wrap)


def inbox_page(wrap):
    return render_inbox(wrap)
