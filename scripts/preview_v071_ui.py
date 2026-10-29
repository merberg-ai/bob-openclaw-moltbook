#!/usr/bin/env python3
"""Preview the actual v0.7.1 Activity Manager on localhost with fake data.

The parent creates a private temporary HOME and the checksum-verified candidate,
then launches a separate, clean-environment child with all POST actions disabled.
No real Bob configuration, credential, database, live service or Moltbook API is
accessed. Stop with Ctrl+C. This is a development preview, NOT an installer.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
from http.client import HTTPConnection
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading

import build_v071_manager_candidate as builder
from rehearse_v071_ui_update import inspect_package

PREFIX = "bob-v071-preview-"
MARKER = {"type": "bob-v071-readonly-browser-preview", "production_allowed": False}
ROUTES = frozenset({"/", "/activity", "/originals", "/healthz"})
FAKE_ID = "00000000-0000-4000-8000-000000000071"
FAKE_STAMP = "20261028T120000Z"


def save(path: Path, data: bytes, mode: int = 0o600) -> None:
    if path.is_symlink() or path.exists():
        raise ValueError("Preview file already exists")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(fd, "wb") as out:
        out.write(data)


def prepare(root: Path) -> dict[str, str]:
    if (root.is_symlink() or not root.name.startswith(PREFIX)
            or not root.is_dir() or any(root.iterdir())
            or stat.S_IMODE(root.stat().st_mode) & 0o077):
        raise ValueError("Preview requires a new private temporary directory")
    manager, nav = builder.build()
    # Re-validate ZIP membership, both checksums and pinned source relation.
    actual_manager, actual_nav = inspect_package(builder.review_zip(manager, nav))
    if (actual_manager, actual_nav) != (manager, nav):
        raise ValueError("Preview package differs from checked source")
    save(root / "PREVIEW-MARKER.json", json.dumps(MARKER, sort_keys=True).encode())
    save(root / "bin/bob-activity-manager", manager, 0o700)
    save(root / "bin/navigation_shell.py", nav)
    (root / "home/.config/moltbook").mkdir(mode=0o700, parents=True)
    feed = b'{"sample":true,"source":"synthetic-only"}\n'
    feed_sha = hashlib.sha256(feed).hexdigest()
    draft = "A synthetic comment draft for checking Bob's responsive interface. Not a real post."
    record = {
        "schema": 2,
        "run_id": FAKE_STAMP,
        "status": "pending",
        "chosen_post_id": FAKE_ID,
        "chosen_title": "Preview: an imaginary discussion",
        "chosen_author": "Demo Agent",
        "chosen_submolt": "general",
        "why": "Synthetic example demonstrating why Bob selected a post.",
        "draft_comment": draft,
        "draft_sha256": hashlib.sha256(draft.encode()).hexdigest(),
        "snapshot_file": f"scout-feed-{FAKE_STAMP}.json",
        "snapshot_sha256": feed_sha,
        "approval_sha256": hashlib.sha256(
            (FAKE_ID + "\n" + draft + "\n" + feed_sha).encode()).hexdigest(),
        "captured_excerpt": "No external post was fetched. Everything here is a dummy.",
        "validation_errors": [],
    }
    folder = root / "home/.config/moltbook"
    save(folder / f"scout-feed-{FAKE_STAMP}.json", feed)
    save(folder / f"scout-result-{FAKE_STAMP}.json",
         json.dumps(record, sort_keys=True).encode())
    return {
        "manager_sha256": builder.sha256(manager),
        "navigation_sha256": builder.sha256(nav),
        "preview_only": "true",
    }


def assert_private(root: Path) -> None:
    if (not root.is_absolute() or root.is_symlink()
            or not root.name.startswith(PREFIX) or not root.is_dir()
            or stat.S_IMODE(root.stat().st_mode) & 0o077):
        raise ValueError("Invalid private preview sandbox")
    marker = root / "PREVIEW-MARKER.json"
    if marker.is_symlink() or json.loads(marker.read_text()) != MARKER:
        raise ValueError("Missing preview-only marker")
    manager = root / "bin/bob-activity-manager"
    module = root / "bin/navigation_shell.py"
    if any(x.is_symlink() or not x.is_file() for x in (manager, module)):
        raise ValueError("Missing safe candidate files")
    candidate, nav = builder.build()
    if (manager.read_bytes(), module.read_bytes()) != (candidate, nav):
        raise ValueError("Preview candidate source changed")


def seed_synthetic_views(module, root: Path) -> None:
    """Populate only the throwaway HOME's SQLite with fake dashboard content."""
    expected = (root / "home/.config/moltbook").resolve()
    if (module.DATA.resolve() != expected
            or Path.home().resolve() != (root / "home").resolve()):
        raise ValueError("Refusing to seed anything outside the preview sandbox")
    t = "2026-10-28T12:00:00+00:00"
    with module.publish_conn() as db:
        module.original_init(db)
        db.execute(
            "INSERT INTO publish_jobs "
            "(run_id,approval_sha256,post_id,draft_comment,mode,state,"
            "created_at,attempted_at,comment_id,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("20261027T120000Z", "0" * 64, FAKE_ID,
             "A fictional published comment for the layout preview.",
             "manual", "published", t, t, FAKE_ID, t),
        )
        db.execute(
            "INSERT INTO published_replies "
            "(id,post_id,comment_id,author,content,detected_at) "
            "VALUES (?,?,?,?,?,?)",
            ("sample-reply", FAKE_ID, FAKE_ID,
             "Example Reader", "Synthetic reply, never retrieved from Moltbook.", t),
        )
        db.execute(
            "INSERT INTO original_requests "
            "(id,kind,state,created_at,completed_at) VALUES (?,?,?,?,?)",
            ("a" * 24, "thought", "completed", t, t),
        )
        title = "Preview: Bob's imaginary original post"
        content = (
            "This sample original post exists only in a temporary demonstration "
            "database. It is included to exercise the draft editor, approval "
            "buttons, long content wrapping and narrow mobile layouts."
        )
        digest = hashlib.sha256(
            ("general\n" + title + "\n" + content).encode()).hexdigest()
        db.execute(
            "INSERT INTO original_posts "
            "(id,request_id,submolt,title,content,digest,state,source,"
            "created_at,updated_at,visible) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("b" * 24, "a" * 24, "general", title, content, digest,
             "draft", "synthetic preview", t, t, 0),
        )
        db.execute(
            "INSERT INTO publish_events (at,kind,details) VALUES (?,?,?)",
            (t, "preview_event", "Synthetic-only activity for layout review"),
        )


def make_server(root: Path):
    # Called only in the child with HOME set to the synthetic directory.
    assert_private(root)
    if Path.home().resolve() != (root / "home").resolve():
        raise ValueError("Preview must use synthetic HOME")
    manager = root / "bin/bob-activity-manager"
    spec = importlib.util.spec_from_file_location("bob_v071_readonly_preview", manager)
    # Extensionless Python executable requires explicit SourceFileLoader.
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("bob_v071_readonly_preview", str(manager))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    seed_synthetic_views(module, root)
    from http.server import ThreadingHTTPServer

    class ReadOnlyPreview(module.Handler):
        def _send(self, status, message, typ="text/plain; charset=utf-8"):
            # This banner is preview-only and never part of production code.
            if status == 200 and typ == "text/html; charset=utf-8":
                banner = (
                    '<div role="status" style="padding:12px;border:1px solid '
                    '#cda96f;border-radius:9px;background:#382f21;color:#ffe2a5;'
                    'margin-bottom:16px"><strong>DEMO PREVIEW ONLY</strong> '
                    'Synthetic data. Publishing, approvals and generation '
                    'are disabled.</div>'
                )
                marker = '<main class="bob-content" id="main-content" tabindex="-1">'
                if message.count(marker) != 1:
                    raise ValueError("Unexpected preview HTML layout")
                message = message.replace(marker, marker + banner, 1)
            return super()._send(status, message, typ)

        def do_POST(self):
            self._send(405, "Read-only preview: publishing and approvals are disabled")

        def do_GET(self):
            if self.path not in ROUTES:
                self._send(404, "Preview route unavailable")
                return
            super().do_GET()

        def log_message(self, fmt, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyPreview)
    # The generated server validates Host headers; only the chosen loopback
    # listener is allowed, never a LAN address or the real manager port.
    module.ALLOWED_HOSTS = {
        f"127.0.0.1:{server.server_port}",
        f"localhost:{server.server_port}",
    }
    return server


def smoke(server) -> None:
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        for route in sorted(ROUTES):
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            conn.request("GET", route)
            result = conn.getresponse()
            body = result.read().decode()
            if result.status != 200:
                raise AssertionError("Preview GET route failed")
            if route != "/healthz":
                if ('DEMO PREVIEW ONLY' not in body or 'class="bob-layout"' not in body
                        or ('name="csrf"' not in body and route != "/activity")):
                    raise AssertionError("Preview markup missing")
                expected_text = {
                    "/": "Preview: an imaginary discussion",
                    "/activity": "Synthetic reply, never retrieved from Moltbook.",
                    "/originals": "Preview: Bob&#x27;s imaginary original post",
                }[route]
                if expected_text not in body:
                    raise AssertionError("Synthetic preview page not populated")
            conn.close()
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        conn.request("POST", "/originals/request/intro", body="confirmation=test")
        denied = conn.getresponse()
        denied.read()
        if denied.status != 405:
            raise AssertionError("Preview POST was not rejected")
        conn.close()
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        conn.putrequest("GET", "/", skip_host=True)
        conn.putheader("Host", "untrusted.example")
        conn.endheaders()
        forbidden = conn.getresponse()
        forbidden.read()
        if forbidden.status != 403:
            raise AssertionError("Preview accepted arbitrary Host")
        conn.close()
    finally:
        server.shutdown()
        worker.join(timeout=4)


def child_main(root: Path, self_test: bool) -> int:
    server = make_server(root)
    try:
        if self_test:
            smoke(server)
            print("READ-ONLY UI BROWSER PREVIEW: PASS")
            print("Routes: /, /activity, /originals, /healthz")
            print("POST disabled: YES; invalid Host rejected: YES")
        else:
            print(f"Open in Windows browser: http://127.0.0.1:{server.server_port}/",
                  flush=True)
            print("Synthetic data only. POST actions disabled. Ctrl+C to stop.", flush=True)
            server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("Read-only UI preview stopped.", flush=True)
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="Exercise local GET and denied POST; then exit")
    parser.add_argument("--_private-child", type=Path,
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as unprivileged OpenClawLab user")
    try:
        if args._private_child:
            if os.environ.get("BOB_V071_PREVIEW_CHILD") != "1":
                raise ValueError("Private child invocation required")
            return child_main(args._private_child, args.self_test)
        with tempfile.TemporaryDirectory(prefix=PREFIX) as temp:
            root = Path(temp)
            prepare(root)
            # No inherited HOME, Bob credentials, proxy, API keys, or PATH
            # overrides are forwarded to the preview process.
            env = {
                "HOME": str(root / "home"),
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": os.pathsep.join((
                    str(root / "bin"), str(builder.HERE / "src/lib/bob"))),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
                "BOB_MANAGER_BIND": "127.0.0.1",
                "BOB_MANAGER_PORT": "0",
                "BOB_V071_PREVIEW_CHILD": "1",
            }
            child = [
                sys.executable, str(Path(__file__).resolve()),
                "--_private-child", str(root),
            ]
            if args.self_test:
                child.append("--self-test")
            try:
                proc = subprocess.run(child, env=env, cwd=root, check=False,
                                      timeout=15 if args.self_test else None)
            except KeyboardInterrupt:
                return 0
            if proc.returncode:
                raise RuntimeError("Read-only preview child failed")
    except (OSError, ValueError, RuntimeError, AssertionError,
            json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print("READ-ONLY UI PREVIEW REFUSED:", type(exc).__name__,
              "(live installation untouched)", file=sys.stderr)
        return 1
    print("Private preview state removed. No real Bob, Moltbook or service change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
