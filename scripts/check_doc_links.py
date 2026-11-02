#!/usr/bin/env python3
"""Fail if any relative markdown link in the repo points at a missing file."""
from __future__ import annotations
import os, re, subprocess, sys
LINK = re.compile(r'\]\(([^)#\s]+)(?:#[^)\s]*)?\)')

def main() -> int:
    files = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True,
                           check=True).stdout.split()
    bad = []
    for md in files:
        text = open(md, encoding="utf-8").read()
        for m in LINK.finditer(text):
            t = m.group(1)
            if re.match(r"[a-z]+:", t) or t.startswith("/"):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(md), t))):
                bad.append(f"{md}: {t}")
    print("\n".join(bad) or f"all relative links OK in {len(files)} markdown files")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
