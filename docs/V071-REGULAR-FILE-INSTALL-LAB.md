# v0.7.1 regular-file installer integration lab

The live Activity Manager launches a **regular-file** Python script, not a release-pointer symlink. This milestone adds `scripts/rehearse_v071_regular_file_installer.py`: a disposable, regular-file two-file installation transaction exercising the actual pinned baseline bytes, generated candidate bytes, and the navigation module.

The lab writes a durable JSON journal before changing either installed file, uses fsynced per-file atomic replacements and an exclusive transaction lock, handles interruptions after navigation installation or manager replacement, and restores original code while removing newly installed navigation on failed health. Changed installed bytes cause a refusal instead of clobber. On successful candidate health simulation the two installed files remain. No systemd or production manager is touched. Health verdicts are simulated in this lab, not real HTTP checks.

## Acceptance command

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/rehearse_v071_regular_file_installer.py && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_regular_file_installer.py --scenario healthy && python3 scripts/rehearse_v071_regular_file_installer.py --scenario failed-health && python3 scripts/rehearse_v071_regular_file_installer.py --scenario crash-navigation && python3 scripts/rehearse_v071_regular_file_installer.py --scenario crash-manager"
```

Expected 260 tests (252 prior + 8), pending host validation, and four `v0.7.1 REGULAR-FILE INSTALL LAB: PASS` reports.

## Remaining approval gates

A live installer is **not included**. Before any production upgrade implement and validate an authenticated production HTTP probe, systemd controlled restart and rollback integration, durable on-disk recovery state inside an approved production-only private directory, detailed filesystem owner/path checks, ability to recover interrupted writes even if journaling was interrupted between filesystem operations, verified immutable baseline copies, and separate live-change authorization. The recurrent preview sync error must be diagnosed independently.

Production execution available: **NO**.
