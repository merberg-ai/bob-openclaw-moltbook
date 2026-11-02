# v0.7.0 Phase 3: Private installed-source staging

The operator's 2026-10-28 host inventory found 9 installed source files, 15 systemd files/drop-ins, and 8 SQLite tables. The private online backup and isolated restore rehearsal succeeded.

Before importing source to the **public** repository, we need an exact, immutable reference to the currently installed source scripts. This step copies only approved executable/source candidates into a private archive after matching each file against its SHA-256 in the first inventory. It does not install, restart, publish, or alter the live files.

## Run in Windows PowerShell

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && git pull --ff-only && python3 scripts/stage_live_sources.py"
~~~

Expected output includes:

~~~text
Private source snapshot: /home/openclaw/.local/state/bob-baseline/source-staging/bob-source-review-....tar.gz
Files: 9 source bytes: ...
Potential hard-coded secret indicators: ...
MANUAL REVIEW REQUIRED. Never upload or commit this raw archive.
Live sources, services and SQLite were not modified.
~~~

The report is kept private on the WSL machine. **Do not upload the tarball to GitHub, a pull request, email or this chat until the exact files have been manually reviewed for embedded credentials, personal information and machine-specific configuration.** An automated scan is only a warning, not a guarantee of safety.

Each source file is rehashed against the original inventory. If a file changed, staging fails rather than silently importing an unrecorded new revision; rerun the inventory and investigate instead. The archive contains only code from the expected Bob executable/library locations. It deliberately excludes systemd unit contents, Linux and Windows credentials, private configuration, SQLite data, logs and Moltbook feed snapshots.

The private directory and archive are restricted to mode 0700 and 0600 respectively. All archives are local-only.

## What this step does not prove

- It does not discover code files missed by the initial nonrecursive scanner.
- It does not capture Windows startup tasks or scripts.
- It does not prove absence of hardcoded secrets, unsafe dependencies or injection issues.
- It does not compare deployed source with the historical v0.6 reference.
- It is not a deployable release or a replacement for backups.

Next, review the staging result, inventory additional dependencies and Windows startup assets, then sanitize and import canonical source files to a development branch with test fixtures and no private data.
