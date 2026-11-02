# v0.7.1 two-file versioned staging acceptance

The operator accepted the responsive browser preview and confirmed 141 tests, a pinned live manager hash, a private intact SQLite backup, and a running Activity Manager. Read-only systemd classification confirms a direct manager reference and **existing drop-ins**.

## Run this next in the isolated v0.7.1 checkout

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/accept_v071_two_file_staging.py"
```

The acceptance script creates a fresh temporary private release directory. It verifies the exact two-file review archive and original pinned manager, stages both candidate files, atomically selects the candidate symlink, checks compile and integration layout, and then rolls the code selection back to the baseline. It removes all staged files at exit.

The tests deliberately remove or alter the navigation file and verify the operation refuses partial/invalid candidate layouts. No real systemd unit is loaded, no real services restarted, and no Moltbook or real SQLite is contacted. This is **offline staging**, not a production installer or proof of a live Python import.

## Still required before any live update

- Inspect the *effect* of the existing systemd drop-ins on launch/import paths without exposing raw private values.
- Design a restricted, versioned, two-file production installer that refuses unexpected existing files and checks source/backup hashes before any switch.
- Verify that the launched process imports the sibling navigation module and responds correctly, including protected LAN flows, in an isolated service test.
- Agree on health gates, exact restart/rollback behavior, and explicit production approval.

The release review ZIP is intentionally marked `deployable: false`; never copy it over a live manager executable manually.
