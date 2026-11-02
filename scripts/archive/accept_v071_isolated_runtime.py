#!/usr/bin/env python3
"""Run isolated v0.7.1 runtime and rollback acceptance; no production access."""
from __future__ import annotations
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    ("installed_layout", "rehearse_v071_installed_layout.py",
     "v0.7.1 INSTALLED LAYOUT REHEARSAL: PASS"),
    ("browser_runtime", "preview_v071_ui.py",
     "READ-ONLY UI BROWSER PREVIEW: PASS"),
)

def execute(runner=subprocess.run) -> dict[str, bool]:
    results = {}
    for name, filename, marker in SCRIPTS:
        path = ROOT / "scripts" / filename
        args = [sys.executable, str(path)]
        if filename == "preview_v071_ui.py":
            args.append("--self-test")
        try:
            completed = runner(
                args, cwd=str(ROOT), capture_output=True, text=True, timeout=45,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                     "HOME": os.environ.get("HOME", str(Path.home())),
                     "LANG": "C", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            passed = completed.returncode == 0 and marker in completed.stdout
        except (OSError, subprocess.TimeoutExpired):
            passed = False
        results[name] = passed
        if not passed:
            break
    return results

def main() -> int:
    result = execute()
    for name, status in result.items():
        print(name + ":", "PASS" if status else "REFUSED")
    passed = len(result) == len(SCRIPTS) and all(result.values())
    print("v0.7.1 ISOLATED RUNTIME GATE:", "PASS" if passed else "REFUSED")
    print("No systemd service, production database, real credentials or Moltbook publishing used.")
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
