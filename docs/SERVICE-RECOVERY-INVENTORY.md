# v0.7.0: Service topology, startup discovery and local checkout reconciliation

The verified nine-source baseline was published through the connected GitHub integration as remote commit `f3db4b445f379f997f950976576c6a5289e11774`. The operator's clean local checkout instead has commit `28073f1` on the same parent. Both commits contain identical application code, but different commit IDs. Never `git pull` these divergent commits blindly.

## Step A: Safe local checkout reconciliation

Run this **only** from the OpenClawLab feature checkout, never in the live installed source directory:

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && git fetch origin && git show origin/feature/v0.7.0-host-inventory:scripts/reconcile_dev_checkout.py | python3 -"
~~~

The script refuses to reset unless ALL conditions pass: correct checkout and feature branch; clean worktree; HEAD starts with the precise known local commit `28073f1`; the local commit tree exactly matches reviewed remote commit `f3db4b4`; and the fetched remote feature branch descends from `f3db4b4`. It preserves the local commit as `backup/v070-reviewed-local-28073f1` before moving the **development checkout only** to the remote feature head. It refuses unexpected files and changes rather than risking a destructive reset.

The installed executable scripts under `~/.local/bin`, systemd services and timers, SQLite database, live credentials, and publishing settings are not modified.

## Step B: Read-only service topology

After Step A reports success:

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && python3 scripts/inventory_service_topology.py"
~~~

This creates a private 0600 JSON report in `~/.local/state/bob-baseline`, showing known Bob/OpenClaw service and timer filenames, scopes, hashes, dependency links, and whether common security controls and environment directives exist. It never stores raw unit bodies, passwords, Environment= values, ExecStart arguments or full command paths. It does not start/stop anything. The console prints only total counts and duplicate-scope unit names, not private details.

An older inactive system-level Bob scout unit was previously seen beside active user-level scout units. A duplicate service name across user/system scopes must be evaluated, but is NOT a reason to delete the legacy unit without first proving restart/reboot recovery.

## Step C: Read-only Windows startup discovery

Use Windows PowerShell for this step. To avoid WSL drive mounting, copy the checked-in PowerShell script from WSL into a temporary **Windows-local** path and execute it locally:

~~~powershell
$script = Join-Path $env:TEMP 'bob-windows-startup-review.ps1'
wsl -d OpenClawLab -u openclaw -- bash -lc "cat ~/bob-v070-inventory/scripts/inventory_windows_startup.ps1" | Set-Content -Encoding UTF8 -Path $script
if ($LASTEXITCODE -ne 0) { throw 'Windows startup script transfer failed' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script
~~~

The Windows collector reads scheduled tasks, Run registry entries, and startup-folder filenames. It selects entries with Bob/OpenClaw/WSL-distro signatures and saves only category, a safe task label (or hidden placeholder), state, action type and trigger type. It **never records action arguments, registry values, full executable paths, credentials or Windows user identity**. The output is a private JSON under `%LOCALAPPDATA%\BobBaseline` and the console prints only counts and query warnings. It cannot prove startup/recovery works, only show obvious launch mechanisms.

These checks use no external APIs and require no GitHub authentication in WSL. They cannot trigger Moltbook publishing. **Do not upload the private JSON reports to GitHub.** The console summaries can be shared for planning the next safe service-template collection and reboot acceptance phase.
