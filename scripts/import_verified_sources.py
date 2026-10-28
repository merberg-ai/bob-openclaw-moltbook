#!/usr/bin/env python3
"""Import a fixed reviewed Bob source ZIP into the development Git checkout.

Never installs into ~/.local, calls Moltbook, restarts services, commits or pushes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import zipfile

# Candidate file fingerprints verified from the operator's private 2026-10-28 ZIP.
SOURCES = {
    "bin/bob-activity-manager": "9f75535bc013c9ea7ab7582e0adfad3e78d6a7ce769a5b14c66b949c5542e65c",
    "bin/bob-lan-config": "b288e42d6d3add18941242bb54f5f9b96d9dbd2b1a80ef52003a041e03ff6156",
    "bin/bob-moltbook-publisher": "10adeab14cc32f0da1fa06249a59d3998c7bc220d3afd971cfda98ea11a674e0",
    "bin/bob-moltbook-scout": "b37d8b3dfb6d3d8e86a2532a3b0e4c7d7648bc9a01bec4ff4d2d47edfc681afb",
    "bin/bob-original-worker": "fa04eea0ac1218e57ddc1beff86cd10773665af37d476f12d813dcbd88dbaaee",
    "bin/bobctl": "106bdb10b3de0db134c6fea25cf8b4a459013e26a322833db03c53c5d07f6c70",
    "lib/bob/bob_moltbook_api.py": "5df65cf5b203ea0f3c9ba002b4bb94feed96d5952ece5bf2f1a4c367257f3736",
    "lib/bob/bob_originals.py": "6d60a008b0c38d9010b21a624e97f1fdaa2c3113567f88440d58c8e34ca85c0f",
    "lib/bob/bob_publish_common.py": "ec0cc78e33a92384f57d715c21692cfd384a4efdbc8b29d255b1fc7d0373de6a",
}
MANIFEST = "REVIEW-MANIFEST.json"
MAX_INPUT = 2 * 1024 * 1024
MAX_SOURCE = 2 * 1024 * 1024


def preflight(raw: bytes) -> dict[str, bytes]:
    if len(raw) > MAX_INPUT:
        raise ValueError("Archive exceeds permitted size")
    contents: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        infos = bundle.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)) or set(names) != set(SOURCES) | {MANIFEST}:
            raise ValueError("Archive membership differs from reviewed candidate")
        meta = None
        for item in infos:
            kind = (item.external_attr >> 16) & 0o170000
            if item.is_dir() or kind not in (0, stat.S_IFREG):
                raise ValueError("Archive contains a non-regular member")
            if item.file_size > MAX_SOURCE:
                raise ValueError("Archive member exceeds size cap")
            data = bundle.read(item)
            if item.filename == MANIFEST:
                meta = json.loads(data)
            else:
                if hashlib.sha256(data).hexdigest() != SOURCES[item.filename]:
                    raise ValueError("Source fingerprint mismatch: " + item.filename)
                compile(data, item.filename, "exec")
                contents[item.filename] = data

        if not isinstance(meta, dict) or meta.get("source_count") != 9:
            raise ValueError("Review manifest missing or invalid")
        if meta.get("changed_file") != "bin/bob-lan-config" or meta.get("changed_lines") != [39, 44]:
            raise ValueError("Unexpected candidate sanitization")
        listed = meta.get("sources")
        if not isinstance(listed, list) or len(listed) != 9:
            raise ValueError("Unexpected manifest files")
        by_name = {row["path"]: row for row in listed}
        if set(by_name) != set(SOURCES):
            raise ValueError("Manifest source list mismatch")
        for name, sha in SOURCES.items():
            if by_name[name].get("candidate_sha256") != sha:
                raise ValueError("Manifest source fingerprint differs")
    if contents["bin/bob-lan-config"].decode("utf-8").count("print('LAN password: [masked]')") != 2:
        raise ValueError("Password masking differs from approved copy")
    return contents


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True,
                            text=True, check=True, timeout=12)
    return result.stdout.strip()


def require_clean_feature_branch(root: Path) -> None:
    if git(root, "branch", "--show-current") != "feature/v0.7.0-host-inventory":
        raise ValueError("Refusing to modify a different branch")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ValueError("Not at this project's Git root")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Working tree has local changes; refusing to overwrite")
    if (root / "src").exists() or (root / "src").is_symlink():
        raise FileExistsError("src/ already exists")


def import_to_checkout(root: Path, sources: dict[str, bytes]) -> None:
    # Write into temporary staging, then atomically rename into Git worktree.
    with tempfile.TemporaryDirectory(dir=root, prefix=".bob-source-import-") as scratch:
        base = Path(scratch)
        for filename, content in sources.items():
            target = base / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o755 if filename.startswith("bin/") else 0o644)
        os.rename(base, root / "src")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdin-base64", required=True, action="store_true")
    parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as the unprivileged openclaw user")
    root = Path(__file__).resolve().parents[1]
    try:
        encoded = sys.stdin.buffer.read(MAX_INPUT * 2 + 1)
        if len(encoded) > MAX_INPUT * 2:
            raise ValueError("Encoded archive too large")
        sources = preflight(base64.b64decode(encoded.strip(), validate=True))
        require_clean_feature_branch(root)
        import_to_checkout(root, sources)
    except (OSError, ValueError, RuntimeError, SyntaxError,
            zipfile.BadZipFile, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print("SOURCE IMPORT REFUSED:", type(exc).__name__,
              "(no live files or services changed)", file=sys.stderr)
        return 1
    print("Reviewed source imported into DEVELOPMENT checkout: 9 files")
    print("Masked LAN password display in src/bin/bob-lan-config")
    print("Not committed or pushed; no live installation or service changes.")
    print("Review/test Git changes before public push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
