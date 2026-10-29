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

The Windows collector reads scheduled tasks, Run registry entries, and startup-folder filenames. It selects entries with Bob/OpenClaw/WSL-distro signatures. For matching `.lnk` shortcuts, it now inspects target and arguments **in memory only** to classify the launcher (for example WSL or PowerShell) and whether `OpenClawLab` was mentioned. Those raw strings are never saved or printed. Script-wrapper contents are not inspected. It saves only category, a safe task label (or hidden placeholder), state, action type and trigger type. It **never records action arguments, registry values, full executable paths, credentials or Windows user identity**. The output is a private JSON under `%LOCALAPPDATA%\BobBaseline` and the console prints only counts and query warnings. It cannot prove startup/recovery works, only show obvious launch mechanisms.

These checks use no external APIs and require no GitHub authentication in WSL. They cannot trigger Moltbook publishing. **Do not upload the private JSON reports to GitHub.** The console summaries can be shared for planning the next safe service-template collection and reboot acceptance phase.

## Follow-up after first Windows scan (2026-10-28)

Initial host scan returned zero matching scheduled tasks, zero Run entries, and two matching Startup-folder items, with no query errors. The second scan classified `Bob OpenClaw Startup` as a **PowerShell** shortcut and `OpenClaw Companion` as **other**, with no direct `wsl` or `OpenClawLab` mention in either shortcut's arguments. That points toward possible **Windows interactive-logon** startup, not necessarily machine boot. The first scan did **not** inspect shortcut targets; run the updated collector and compare its two safe launch classifications with the WSL systemd summary before deciding whether Bob can recover from a cold reboot or from WSL shutdown.

The newest collector additionally examines a small, local PowerShell `-File` script when referenced by a matching `.lnk`. It reports only whether that wrapper mentions WSL, `OpenClawLab` or systemd; it does not execute the script or save its contents. `wrapper=unavailable` means it could not safely inspect the script, **not** that no WSL launch occurs. For `other`, the collector reports the executable type and whether its *filename* mentions OpenClaw without disclosing its actual name or full path.

To re-run the improved checks without changing the live installation, start from the **already reconciled** WSL feature checkout and use:

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && GIT_TERMINAL_PROMPT=0 git pull --ff-only && python3 scripts/inventory_service_topology.py"
if ($LASTEXITCODE -ne 0) { throw 'Linux service inventory failed; Windows phase not started.' }
$script = Join-Path $env:TEMP 'bob-windows-startup-review.ps1'
wsl -d OpenClawLab -u openclaw -- bash -lc "cat ~/bob-v070-inventory/scripts/inventory_windows_startup.ps1" | Set-Content -Encoding UTF8 -Path $script
if ($LASTEXITCODE -ne 0) { throw 'Startup script transfer failed.' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script
if ($LASTEXITCODE -ne 0) { throw 'Windows startup audit failed.' }
~~~

The console contains only unit counts/duplicate scope names and classified Startup-folder entries. Share that console output for the next architectural decision. Never upload the private reports, or raw shortcut targets/arguments, to a public repository.

## Verified host topology (2026-10-28)

The operator successfully reconciled the separate WSL development checkout and ran both host collectors.

- systemd: **15 files/drop-ins across 12 scope-qualified units**; 10 user-scope and 2 system-scope, with no expected names missing.
- Both `bob-moltbook-scout.service` and `bob-moltbook-scout.timer` exist in **both scopes**. Presence is not equivalent to enabled or active.
- Windows: 0 matching scheduled tasks, 0 Run registry entries, and 2 user Startup-folder shortcuts, without query warnings.
- `Bob OpenClaw Startup` is a PowerShell shortcut; its safely inspected local wrapper references **WSL, OpenClawLab, and systemd**.
- `OpenClaw Companion` references an OpenClaw-named executable. No WSL command was present directly in that shortcut's arguments.

These findings identify the likely **Windows user logon → PowerShell wrapper → WSL OpenClawLab → systemd** chain. They **do not** establish unattended boot-to-login recovery, actual unit enablement states, Companion behavior, or systemd startup order.

### Next: exact active/enabled status, no fresh inventory required

After syncing the **clean development checkout** with GitHub:

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && GIT_TERMINAL_PROMPT=0 git pull --ff-only && python3 scripts/report_service_readiness.py --report /home/openclaw/.local/state/bob-baseline/inventory-20261028T144113282656Z-93497.json"
~~~

The checker reads the existing private topology report; queries read-only `systemctl show` for only expected Bob units and `loginctl show-user` for the boolean `Linger` state. It prints only allowlisted categories for loaded/active/substate/enabled, no command arguments, environment values, private contents or paths, and changes no services.

An active or enabled system-scope scout alongside the user-scope scout needs a closer look before changing either. `Linger=yes` supports a user systemd manager **after WSL starts**; it cannot make Windows boot WSL. A failed or unknown status is diagnostic, not proof of absence.

Keep both private inventories out of public GitHub; share only the console summary.
