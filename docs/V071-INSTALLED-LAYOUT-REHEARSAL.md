# v0.7.1 installed-layout transaction rehearsal (offline only)

Operator acceptance: 155 existing offline tests pass. Unit source inspection found a direct ExecStart, inline Environment and a custom WorkingDirectory, with no EnvironmentFile, ExecStartPre, ExecStartPost, or ExecCondition in inspected unit sources. These are source-presence observations, not a full proof of effective runtime settings.

This increment exercises a **synthetic installed-layout transaction**, not a production installer. It preserves the original manager executable, stages the generated manager and navigation module together in a private versioned release, switches a synthetic link, and simulates a failed health check and rollback. Nothing calls systemd or Moltbook, and no real credentials or SQLite files are opened.

Run from PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_installed_layout.py"
```

Expected: 159 offline tests and `v0.7.1 INSTALLED LAYOUT REHEARSAL: PASS`.

**Important distinction:** The existing user-systemd unit references the installed manager directly. A symlink created in an unrelated staging directory does **not** redirect that service. A production installer must explicitly establish and verify the effective service launch path, honor existing drop-ins/working directory/environment, and ensure the module import path is valid. It must also implement actual service lifecycle health/rollback gates, preserve the SQLite state, reject unapproved changes, and be separately authorized before any live service switch.

Do not manually copy this candidate or change `ExecStart`; the reviewed ZIP is deliberately non-deployable.
