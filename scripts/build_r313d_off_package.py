#!/usr/bin/env python3
"""Deterministic versioned R3 Off-first package builder, no install or network.

This build is separate from the installed R2 Shadow4 bundle, preserving its
exact hash and activation pointer. The updater may later install the outputs
only via a separately selected, owner-approved R3 release manifest.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "__init__.py", "core.py", "evidence.py", "digest.py", "shadow.py",
    "r3_cutover_rehearsal.py", "r3_unified.py", "r35_migration_lab.py",
    "r36_admission_contract.py", "r37_trusted_gate_lab.py",
    "r39_publisher_review.py", "r313a_private_migration.py",
    "r313b_upgrade_contract.py", "r313c_candidate.py",
    "r313d_staging.py", "r313d_producer.py",
)
MAX_BYTES = 512*1024


def build() -> tuple[bytes,bytes]:
    memory = BytesIO()
    with ZipFile(memory,"w",compression=ZIP_STORED) as archive:
        for name in MODULES:
            # Freeze the historical producer exactly as signed in format1.
            # New source belongs only in the separately reviewed skip1 ZIP.
            path = (ROOT/"release_baselines"/"v08-r3format1"/name
                    if name == "r313d_producer.py"
                    else ROOT/"src"/"bob_v08"/name)
            if path.is_symlink() or not path.is_file():
                raise ValueError("r3_missing_reviewed_module")
            content=path.read_bytes()
            if not 0 < len(content) <= 64*1024:
                raise ValueError("r3_module_oversized")
            compile(content,str(path),"exec")
            info=ZipInfo("bob_v08/"+name,date_time=(1980,1,1,0,0,0))
            info.compress_type=ZIP_STORED
            info.create_system=3
            info.external_attr=0o100644<<16
            archive.writestr(info,content)
    launcher = ROOT/"src"/"bin"/"bob-r3-propose"
    if launcher.is_symlink() or not launcher.is_file():
        raise ValueError("r3_launcher_missing")
    program=launcher.read_bytes()
    compile(program,"bob-r3-propose","exec")
    package=memory.getvalue()
    if not 0 < len(package) <= MAX_BYTES or not 0 < len(program) <= MAX_BYTES:
        raise ValueError("r3_package_oversized")
    return package,program


if __name__ == "__main__":
    import hashlib
    blob,command=build()
    print("R3 OFF-FIRST VERSIONED PACKAGE BUILD: PASS")
    print("modules:",len(MODULES))
    print("archive_sha256:",hashlib.sha256(blob).hexdigest())
    print("archive_bytes:",len(blob))
