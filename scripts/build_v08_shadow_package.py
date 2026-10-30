#!/usr/bin/env python3
"""Deterministic package builder for the *uninstalled* R2 shadow preview.

This is NOT a generated-dashboard patcher. It packages real reviewed Python
modules into an importable zip, compatible with the existing guarded flat-file
updater while the versioned-directory installer is developed and tested.
build() has no installed-file, credential, service or network side effects.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("__init__.py", "core.py", "evidence.py", "digest.py",
           "shadow.py", "inspect.py")
MAX_MODULE = 64 * 1024
BUNDLE = "bob_v08_package.pyz"
ENTRYPOINT = "bob-v08-shadow"

WRAPPER = '''#!/usr/bin/env python3
"""Bob v0.8 guarded shadow-only local launcher. No publisher is imported."""
from pathlib import Path
import json
import sys

PACKAGE = Path(__file__).resolve().parent / "bob_v08_package.pyz"
if PACKAGE.is_symlink() or not PACKAGE.is_file():
    raise SystemExit("Bob v0.8 shadow package unavailable")
sys.path.insert(0, str(PACKAGE))

if __name__ == "__main__":
    if sys.argv[1:] == ["--status"]:
        from bob_v08.inspect import read_status
        print(json.dumps(read_status(), sort_keys=True))
        raise SystemExit(0)
    from bob_v08.shadow import main
    raise SystemExit(main())
'''


def build():
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
        for name in MODULES:
            source = ROOT / "src" / "bob_v08" / name
            if source.is_symlink() or not source.is_file():
                raise ValueError("missing reviewed R2 source")
            data = source.read_bytes()
            if not 0 < len(data) <= MAX_MODULE:
                raise ValueError("oversized R2 source")
            compile(data, str(source), "exec")
            info = ZipInfo("bob_v08/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    package = buffer.getvalue()
    wrapper = WRAPPER.encode("utf-8")
    compile(wrapper, ENTRYPOINT, "exec")
    if len(package) > 512 * 1024 or len(wrapper) > 512 * 1024:
        raise ValueError("R2 bundle exceeds guarded updater cap")
    return package, wrapper


if __name__ == "__main__":
    import hashlib
    bundle, launcher = build()
    print("BOB R2 PACKAGE SOURCE CHECK: PASS")
    print("modules:", ",".join(MODULES))
    print("sha256:", hashlib.sha256(bundle).hexdigest())
    print("launcher_bytes:", len(launcher))
