#!/usr/bin/env python3
"""Parse-check inert staging-only service/timer files with systemd-analyze.

Creates private TemporaryDirectory units with synthetic commands. Never calls
systemctl, systemd-run, daemon-reload, enables/starts services, or accesses
production configuration. No actual service-manager execution is tested here.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from stage_service_graph import PREFIX, create, verify

EXPECTED_COUNT = 10


def verify_with_parser(root: Path, *, executable: str | None = None) -> None:
    verify(root)
    command = executable if executable is not None else shutil.which("systemd-analyze")
    if not command or Path(command).name != "systemd-analyze":
        raise RuntimeError("systemd-analyze missing or not allowed")
    unit_dir = root / "units"
    files = sorted(unit_dir.iterdir())
    if len(files) != EXPECTED_COUNT or any(
            p.is_symlink() or not p.is_file() or not p.name.startswith(PREFIX)
            or p.suffix not in {".service", ".timer"} for p in files):
        raise ValueError("Unexpected staging unit selection")
    # systemd-analyze parses unit text and may inspect dependencies, but does
    # NOT enable/install/start the units. Never send raw diagnostics to console.
    process = subprocess.run(
        [command, "verify", *map(str, files)], cwd=unit_dir,
        capture_output=True, text=True, check=False, timeout=20,
        env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
             "HOME": str(root / "private"), "LC_ALL": "C"},
    )
    if process.returncode != 0:
        raise RuntimeError("Inert unit parser rejected the fixture")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("Refusing to run as root")
    try:
        with tempfile.TemporaryDirectory(prefix=PREFIX) as temp:
            root = Path(temp)
            create(root)
            verify_with_parser(root)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("SYSTEMD INERT UNIT PARSE: REFUSED", type(exc).__name__,
              "(nothing installed or started)", file=sys.stderr)
        return 1
    print("SYSTEMD INERT UNIT PARSE: PASS")
    print("Stage-only services: 6; timers: 4")
    print("systemd-analyze verify: PASS")
    print("No installed units, service-manager execution, credentials or live state changed.")
    print("Temporary stage automatically removed. NOT DEPLOYABLE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
