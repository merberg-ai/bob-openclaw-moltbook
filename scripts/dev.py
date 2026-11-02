#!/usr/bin/env python3
"""Developer entry point for Bob. Offline only: never touches a live host.

    python3 scripts/dev.py test                 # whole suite, parallel
    python3 scripts/dev.py test r4 updater      # by area
    python3 scripts/dev.py test -k schedule     # test files whose name contains 'schedule'
    python3 scripts/dev.py check                # compile everything + manifest sanity + tests
    python3 scripts/dev.py areas                # list areas and file counts

Tests run one module per subprocess with a fixed umask (022) and a clean
environment so results match CI regardless of the shell they run from.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import fnmatch
import json
import os
from pathlib import Path
import py_compile
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

AREAS = {
    "r4": ["test_r4_*"],
    "r3": ["test_r3*", "test_r31*", "test_r35*", "test_r36*", "test_r37*",
           "test_r38*", "test_r39*", "test_r310*", "test_r311*", "test_r312*",
           "test_r313*"],
    "updater": ["test_v08_r1_updater*", "test_bob_updater*", "test_main_updater*",
                "test_*release*", "test_*rollback*"],
    "ui": ["test_navigation*", "test_oc*", "test_*dashboard*", "test_compact*",
           "test_preview*", "test_*http*", "test_ch_https*", "test_ui_*"],
    "memory": ["test_pm*", "test_*memory*", "test_*personality*"],
    "friends": ["test_fm*", "test_*friend*"],
    "tools": ["test_bob_evidence*", "test_dev_*"],
}


def test_files() -> list[Path]:
    return sorted(TESTS.glob("test_*.py"))


def select(areas: list[str], pattern: str | None) -> list[Path]:
    files = test_files()
    if areas:
        unknown = [a for a in areas if a not in AREAS and a != "legacy"]
        if unknown:
            raise SystemExit(f"unknown area(s): {', '.join(unknown)}; see `dev.py areas`")
        claimed = {f for pats in AREAS.values() for f in files
                   if any(fnmatch.fnmatch(f.stem, p) for p in pats)}
        chosen = set()
        for area in areas:
            if area == "legacy":
                chosen |= set(files) - claimed
            else:
                chosen |= {f for f in files if any(fnmatch.fnmatch(f.stem, p) for p in AREAS[area])}
        files = sorted(chosen)
    if pattern:
        files = [f for f in files if pattern in f.stem]
    return files


def _env() -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("BOB_", "OPENCLAW_", "MOLTBOOK_"))}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0", LC_ALL="C.UTF-8")
    return env


def run_module(path: Path) -> tuple[Path, int, float, str]:
    start = time.monotonic()
    old = os.umask(0o022)
    try:
        p = subprocess.run([sys.executable, "-m", "unittest", "-q", f"tests.{path.stem}"],
                           cwd=ROOT, env=_env(), capture_output=True, text=True,
                           timeout=600)
        out = p.stdout + p.stderr
        code = p.returncode
    except subprocess.TimeoutExpired:
        out, code = "TIMEOUT after 600s", 124
    finally:
        os.umask(old)
    return path, code, time.monotonic() - start, out


def cmd_test(args) -> int:
    files = select(args.areas, args.k)
    if not files:
        print("no matching test files")
        return 1
    if os.geteuid() == 0:
        print("WARNING: running as root; several Bob tests intentionally refuse root. "
              "Use a normal user for results that match CI.\n")
    jobs = args.jobs or min(16, (os.cpu_count() or 2) * 2)
    t0 = time.monotonic()
    failed = []
    with ThreadPoolExecutor(jobs) as pool:
        for path, code, secs, out in pool.map(run_module, files):
            mark = "ok  " if code == 0 else "FAIL"
            if code != 0 or args.verbose:
                print(f"{mark} {path.stem} ({secs:.1f}s)")
            if code != 0:
                failed.append((path, out))
    for path, out in failed:
        print(f"\n===== {path.stem} =====\n{out.strip()[-4000:]}")
    print(f"\n{len(files) - len(failed)}/{len(files)} test modules passed "
          f"in {time.monotonic() - t0:.1f}s ({jobs} workers)")
    return 1 if failed else 0


def cmd_areas(_args) -> int:
    files = test_files()
    claimed = set()
    for area, pats in AREAS.items():
        hits = [f for f in files if any(fnmatch.fnmatch(f.stem, p) for p in pats)]
        claimed |= set(hits)
        print(f"{area:9} {len(hits):4}")
    print(f"{'legacy':9} {len(set(files) - claimed):4}  (everything else)")
    return 0


def cmd_check(args) -> int:
    bad = 0
    import tempfile
    scratch = tempfile.mkdtemp(prefix="bob-dev-check-")
    sources = [*ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/*.py"), *ROOT.glob("webui/*.py"),
               *(p for p in (ROOT / "src/bin").iterdir()
                 if p.is_file() and p.read_bytes()[:2] == b"#!" and b"python" in p.read_bytes()[:60])]
    for src in sources:
        try:
            py_compile.compile(str(src), cfile=os.path.join(scratch, "x.pyc"), doraise=True)
        except py_compile.PyCompileError as exc:
            bad += 1
            print("COMPILE", src.relative_to(ROOT), exc.msg.strip().splitlines()[-1])
    print(f"compiled {len(sources)} python sources, {bad} error(s)")
    manifest = json.loads((ROOT / "releases/current.json").read_text())
    for item in manifest["files"]:
        ref = item.get("source") or item.get("builder")
        if not (ROOT / ref).is_file():
            bad += 1
            print("MANIFEST missing", ref)
    print(f"releases/current.json: {manifest['release']} (from {manifest['from']}), "
          f"{len(manifest['files'])} files")
    if bad:
        return 1
    return cmd_test(argparse.Namespace(areas=[], k=None, jobs=args.jobs, verbose=False))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bob offline developer commands")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("test", help="run tests in parallel")
    t.add_argument("areas", nargs="*", help=f"areas: {', '.join([*AREAS, 'legacy'])}")
    t.add_argument("-k", help="only test files whose name contains this text")
    t.add_argument("-j", "--jobs", type=int)
    t.add_argument("-v", "--verbose", action="store_true")
    t.set_defaults(func=cmd_test)
    c = sub.add_parser("check", help="compile all sources, check manifest, run all tests")
    c.add_argument("-j", "--jobs", type=int)
    c.set_defaults(func=cmd_check)
    a = sub.add_parser("areas", help="list test areas")
    a.set_defaults(func=cmd_areas)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
