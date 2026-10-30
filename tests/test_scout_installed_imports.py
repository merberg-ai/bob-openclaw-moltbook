"""Regression: installed Scout/publisher entrypoints must import in isolated WSL layout.

No user installation, service invocation, network calls, credentials or SQLite
access: only copies repository-owned source into a temporary ~/.local/bin analog
and runs the entrypoint under a non-main runpy name.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
MODULES=(
    "bob_job_tracking.py",
    "bob_memory_recall.py",
    "bob_memory.py",
    "bob_friend_scout.py",
    "bob_friend_discovery.py",
    "bob_friends.py",
    "bob_publish_common.py",
    "bob_originals.py",
    "bob_activity_limits.py",
    "bob_moltbook_api.py",
)
ENTRYPOINTS=(
    "bob-moltbook-scout",
    "bob-moltbook-publisher",
    "bob-original-worker",
)


def prepare(path,*,include_common=True):
    for file in MODULES:
        if file=="bob_publish_common.py" and not include_common:
            continue
        source=ROOT/"src/lib/bob"/file
        if not source.is_file():
            raise AssertionError("Missing repository module "+str(source))
        shutil.copyfile(source,path/file)
    for name in ENTRYPOINTS:
        shutil.copyfile(ROOT/"src/bin"/name,path/name)


def check(path,entry):
    # -I prevents development checkout/PYTHONPATH and user site packages
    # from hiding a missing installed module. Never call script main().
    code=(
        "import runpy,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "runpy.run_path(sys.argv[2],run_name='installed_import_smoke');"
        "print('IMPORT_OK')"
    )
    env=dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"]="1"
    env.pop("PYTHONPATH",None)
    return subprocess.run(
        [sys.executable,"-B","-I","-c",code,str(path),str(path/entry)],
        capture_output=True,text=True,env=env,timeout=20,check=False,
    )


class InstalledScoutImports(unittest.TestCase):
    def test_missing_shared_module_reproduces_operator_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            prepare(path,include_common=False)
            result=check(path,"bob-moltbook-scout")
            self.assertNotEqual(result.returncode,0)
            self.assertIn("No module named 'bob_publish_common'",result.stderr)
            self.assertNotIn("IMPORT_OK",result.stdout)

    def test_release_installs_common_to_same_entrypoint_directory(self):
        # This regression checks the dependency fix across FUTURE releases,
        # not that v0.7.5-scout-importfix1 remains the current manifest.
        release_notes=(ROOT/"docs/V075-SCOUT-IMPORT-FIX.md").read_text()
        self.assertIn("v0.7.5-scout-importfix1",release_notes)
        self.assertIn("bob_publish_common.py",release_notes)
        # Source itself is a pure local helper, no Moltbook HTTP or credentials.
        source=(ROOT/"src/lib/bob/bob_publish_common.py").read_text()
        self.assertNotIn("urllib.request",source)
        self.assertNotIn("subprocess",source)
        self.assertNotIn("api_key",source)
        self.assertIn("def connect()",source)
        self.assertIn("def load_record(",source)

    def test_fixed_clean_installed_directory_imports_three_workers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            prepare(path)
            for entry in ENTRYPOINTS:
                with self.subTest(entry=entry):
                    result=check(path,entry)
                    self.assertEqual(result.returncode,0,result.stderr[:4000])
                    self.assertIn("IMPORT_OK",result.stdout)
                    # Importing must not perform a network action or
                    # run a Scout/publisher job.
                    self.assertNotIn("Fetching new Moltbook discussions",result.stdout)


if __name__=="__main__":
    unittest.main()
