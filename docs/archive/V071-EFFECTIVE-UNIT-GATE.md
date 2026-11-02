# v0.7.1 effective service configuration gate

The operator confirmed 145 offline tests and two-file staging acceptance. Read-only service inspection also confirmed a direct Activity Manager reference **and existing user-systemd drop-ins**. Those drop-ins could affect the working directory, environment, execution hooks, or runtime sandbox.

This next inspector deliberately reports **boolean classifications only**. It does not print `ExecStart`, `Environment`, unit paths, credentials, or private service configuration. It does not change systemd, restart a process, or deploy any files.

Run in Windows PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/inspect_v071_effective_unit.py"
```

The classifier reports direct executable reference, drop-ins, custom working directory, environment files/inline environment presence, chroot/root image, dynamic user, user override, and pre/post/condition hooks. A `YES` for a custom launch option is **not an error**, but means the future updater must account for its behavior.

This is deliberately *not* a replacement for independently verifying exact unit/drop-in precedence before production. A separate deployment change must pin the actual service launch contract, stage both manager and navigation in a versioned directory, run authenticated acceptance checks, and offer code-only rollback on failed health. Existing source and SQLite remain intact until separately authorized.
