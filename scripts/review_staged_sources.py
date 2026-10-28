#!/usr/bin/env python3
"""Offline static audit of private Bob source. No code or secret values emitted.

Reports only archive-relative file names, line numbers, signal categories, and
Python import-module names. This is triage, not proof source is safe to publish.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import ipaddress
import json
from pathlib import Path
import re
import sys
import tarfile

from audit_staged_sources import (
    ALLOWED_MEMBER, MANIFEST, MAX_FILE_BYTES, audit_archive, _read_member,
)

PYTHON_SHEBANG = re.compile(rb"^#![^\r\n]*python[0-9.]*(?:\s|$)", re.I)
SHELL_SHEBANG = re.compile(rb"^#![^\r\n]*(?:ba|z|k|da)?sh(?:\s|$)", re.I)
SENSITIVE = re.compile(r"(?:password|passwd|api[_-]?key|token|secret|credential|auth_key)", re.I)
ABSOLUTE = re.compile(r"^(?:/home/|/mnt/[a-z]/|[A-Za-z]:\\)")
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
MODULE = re.compile(r"^[A-Za-z_]\w{0,78}$")


def add_signal(signals: list[dict], name: str, line: int, kind: str) -> None:
    item = {"file": name, "line": int(line), "category": kind}
    if item not in signals:
        signals.append(item)


def nonloopback_ip(value: str) -> bool:
    for match in IPV4.finditer(value):
        try:
            ip = ipaddress.ip_address(match.group())
        except ValueError:
            continue
        if not ip.is_loopback and not ip.is_unspecified:
            return True
    return False


def assigned_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [name for element in node.elts for name in assigned_names(element)]
    return []


def prints_credential(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != "print":
        return False
    return any(
        (isinstance(x, ast.Subscript) and isinstance(x.slice, ast.Constant)
         and isinstance(x.slice.value, str) and SENSITIVE.search(x.slice.value))
        or (isinstance(x, ast.Constant) and isinstance(x.value, str)
            and SENSITIVE.search(x.value))
        for arg in node.args for x in ast.walk(arg)
    )


def review_python(name: str, source: str) -> tuple[list[dict], set[str]]:
    tree = ast.parse(source, filename=name)
    signals: list[dict] = []
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = (
                [s for t in node.targets for s in assigned_names(t)]
                if isinstance(node, ast.Assign) else assigned_names(node.target)
            )
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                if len(value.value) >= 8 and any(SENSITIVE.search(n) for n in targets):
                    add_signal(signals, name, node.lineno, "sensitive-named literal assignment")
        elif isinstance(node, ast.Call):
            if prints_credential(node):
                add_signal(signals, name, node.lineno, "possible credential-related stdout")
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                add_signal(signals, name, node.lineno, "dynamic Python execution")
            if any(k.arg == "shell" and isinstance(k.value, ast.Constant)
                   and k.value.value is True for k in node.keywords):
                add_signal(signals, name, node.lineno, "shell-enabled call; manual review")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if ABSOLUTE.search(node.value):
                add_signal(signals, name, node.lineno, "machine-specific absolute path")
            if nonloopback_ip(node.value):
                add_signal(signals, name, node.lineno, "non-loopback IP literal")
    return signals, imports


def review_shell(name: str, source: str) -> list[dict]:
    signals: list[dict] = []
    for line_number, line in enumerate(source.splitlines(), 1):
        if re.search(r"\b(?:eval|source)\b|\$\(\s*(?:curl|wget)\b", line):
            add_signal(signals, name, line_number, "shell dynamic/source operation")
    return signals


def review_snapshot(archive: Path) -> dict:
    verified = audit_archive(archive)  # Verifies manifest, members, SHA-256.
    entries: list[tuple[str, str, str]] = []
    local_modules: set[str] = set()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            if member.name == MANIFEST:
                continue
            if not ALLOWED_MEMBER.fullmatch(member.name):
                raise ValueError("Unexpected archive member")
            data = _read_member(bundle, member, MAX_FILE_BYTES)
            source = data.decode("utf-8")
            shebang = data.split(b"\n", 1)[0]
            kind = ("shell" if SHELL_SHEBANG.search(shebang) else
                    "python" if member.name.endswith(".py") or PYTHON_SHEBANG.search(shebang)
                    else "unknown")
            entries.append((member.name, kind, source))
            if member.name.startswith("lib/bob/") and member.name.endswith(".py"):
                local_modules.add(Path(member.name).stem)
            if member.name.startswith("bin/"):
                local_modules.add(Path(member.name).name.replace("-", "_"))
    signals: list[dict] = []
    imports: set[str] = set()
    counts: Counter[str] = Counter()
    for name, kind, source in entries:
        counts[kind] += 1
        if kind == "python":
            try:
                findings, modules = review_python(name, source)
            except SyntaxError:
                add_signal(signals, name, 1, "Python syntax unavailable; manual review")
            else:
                signals.extend(findings)
                imports.update(modules)
        elif kind == "shell":
            signals.extend(review_shell(name, source))
        else:
            add_signal(signals, name, 1, "unrecognized script language; manual review")
    stdlib = getattr(sys, "stdlib_module_names", frozenset())
    external = sorted(
        m for m in imports
        if m not in stdlib and m not in local_modules and m != "__future__"
        and MODULE.fullmatch(m) and not SENSITIVE.search(m)
    )
    signals.sort(key=lambda row: (row["file"], row["line"], row["category"]))
    return {
        "files_checked": verified["files_checked"],
        "language_counts": dict(sorted(counts.items())),
        "prior_heuristic_flags": verified["flag_count"],
        "possible_nonstdlib_imports": external,
        "findings": signals,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Private source snapshot (default newest)")
    args = parser.parse_args()
    root = Path.home() / ".local/state/bob-baseline/source-staging"
    if args.archive is None:
        candidates = sorted(root.glob("bob-source-review-*.tar.gz"))
        if not candidates:
            parser.error("No private staged source archive found")
        archive = candidates[-1]
    else:
        archive = args.archive
    try:
        result = review_snapshot(archive)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError,
            tarfile.TarError) as exc:
        print("Source review FAILED (" + type(exc).__name__ + "). No code disclosed.",
              file=sys.stderr)
        return 1
    print("Snapshot verified. Source files:", result["files_checked"])
    print("Script languages:", ", ".join(
        f"{k}={v}" for k, v in result["language_counts"].items()))
    print("Prior heuristic flags:", result["prior_heuristic_flags"],
          "(already reviewed separately)")
    print("Possible non-stdlib modules:",
          ", ".join(result["possible_nonstdlib_imports"]) or "none detected")
    print("Additional static review findings:", len(result["findings"]))
    for item in result["findings"]:
        print(f'{item["file"]}:{item["line"]}: {item["category"]}')
    print("Only relative paths, line numbers, categories and import names printed.")
    print("No source code or credential values printed; private archive unchanged.")
    print("Static review does NOT certify this source safe for publication.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
