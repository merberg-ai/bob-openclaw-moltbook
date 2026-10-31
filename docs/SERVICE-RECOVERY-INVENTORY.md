## G2.5 owner-confirmed internet-side inaccessibility (2026-10-31)

The owner reports that **nothing is reachable from the outside**. This statement adds observed outside-network inaccessibility to previously demonstrated WSL Hyper-V default-block (`Enabled=True`, `DefaultInboundAction=Block`), LAN-scope exception for Bob's TCP 18790 (`192.168.1.0/24`), no Windows netsh portproxy, and working TLS dashboard access from two Windows LAN clients after reboot. This is good operational evidence for keeping Activity Manager private.

Because the owner did not specify testing methodology or whether IPv6, VPN and UPnP were covered, do not claim a comprehensive independent WAN scan, or assert that all possible public network paths are impossible. Revalidate after router, firewall, IPv6 or VPN changes. No need to modify the healthy rules. The separate `code-server` 8787 Hyper-V rule is source `Any`, but no 8787 listener was detected inside OpenClawLab when checked.

Outstanding G2: independently reconcile persisted legacy publisher attempt/reply IDs with real Moltbook posts/receipts and possible duplicate submissions across the reboot. Historical count stayed 23 attempted/0 uncertain at both host snapshots, but this alone doesn't exclude remote duplicates. Do not invoke any publisher POST/oneshot or reset the existing SQLite. Previously reported access from both browsers does not explicitly establish a fresh certificate-warning-free rotated-password login.

---

## G2.5 WSL firewall default-block confirmed, no active 8787 listener (2026-10-31)

New owner-provided effective WSL Hyper-V policy result: `Enabled=True`, `DefaultInboundAction=Block`, `AllowHostPolicyMerge=True` for VMCreatorId `{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}`. Combined with previously verified `Bob Activity Manager - WSL LAN` `Enabled=True/Allow/TCP 18790/RemoteAddresses=192.168.1.0/24`, this supports the intended **default-deny inbound with one LAN-scoped dashboard exception**. This passes the WSL-specific Hyper-V firewall check, but host-policy merge is enabled, so other Windows firewall rules and router/WAN/IPv6/VPN paths are separate review gates.

The owner also ran `wsl.exe -d OpenClawLab -u openclaw -- ss -lnt '( sport = :8787 )'` and saw only the column header: **no current TCP listener on 8787 within that distro**. The unrelated Hyper-V code-server 8787 `Allow/Any` rule remains broader than necessary if unused, but no currently listening service or Internet exposure has been demonstrated. Do not remove it before checking code-server use and other distros if relevant.

**Next nonmutating checks:** review active Windows host firewall allow rules that could match TCP 18790, then check router/NAT/UPnP and public IPv6/VPN exposure. Separately compare persisted legacy attempted/reply IDs to actual Moltbook results across the reboot; unchanged local 23 attempted/0 uncertain cannot independently exclude remote duplicates. Avoid changing the running manager, systemd, certificates, private SQLite or R3 hard-Off settings as part of evidence collection.

---

## G2.5 Hyper-V inbound ACL: Bob 18790 restricted to LAN, code-server 8787 Any (2026-10-31)

The owner reported the installed WSL Hyper-V inbound `Bob Activity Manager - WSL LAN` rule with `Enabled=True`, `Action=Allow`, TCP local port `18790`, and `RemoteAddresses=192.168.1.0/255.255.255.0` (a private `/24`). This strongly supports intentional LAN scoping for the Linux-owned wildcard `0.0.0.0:18790` listener under WSL mirrored networking. The output also included WSL core ICMPv4/ICMPv6 and mDNS rules with `RemoteAddresses=Any`; those are distinct protocols/ports, **not** TCP 18790 overrides.

The same reported list has an unrelated enabled Hyper-V inbound rule named `code-server WSL 8787` permitting TCP local port 8787 from `Any` remote address. That is broader than the Bob rule; by itself it does not prove public reachability, a running service, open router forwarding, or absent authentication.

**Not yet supplied:** the effective `Get-NetFirewallHyperVVMSetting` result, specifically firewall `Enabled`, `DefaultInboundAction` and `AllowHostPolicyMerge`. Do not claim LAN-only proof until the default inbound policy is verified and Windows host/firewall merge, router IPv4 forwarding, global IPv6 and VPN exposure are reviewed. Inspect, don't change:

```powershell
$wslId = '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'
Get-NetFirewallHyperVVMSetting -PolicyStore ActiveStore -Name $wslId |
    Format-List Name,Enabled,DefaultInboundAction,AllowHostPolicyMerge
wsl.exe -d OpenClawLab -u openclaw -- ss -lnt '( sport = :8787 )'
```

The Linux `ss` command checks only whether code-server's listed port is listening, and does not establish exposure or authentication. No service, firewall, Windows portproxy, router or publisher modification is necessary for this evidence collection. A conservative decision on whether to reduce the 8787 rule's remote scope can come after reviewing whether that service is in use. Microsoft Hyper-V firewall reference: https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall .

---

## G2.5 confirmed Linux wildcard listener on WSL mirrored network (2026-10-31)

The owner ran Linux `ss -lnt '( sport = :18790 )'` in OpenClawLab from Windows PowerShell and reported an IPv4 `LISTEN` socket at **`0.0.0.0:18790`**. The owner's `.wslconfig` explicitly sets **`networkingMode=mirrored`**. Combined with confirmed access on two LAN Windows machines and earlier absent Windows host socket/portproxy, this establishes the likely Linux-owned mirrored networking route. It does **not** prove LAN-only restrictions; an IPv4 wildcard socket is not interface-limited.

**Next read-only Hyper-V firewall inspection in ordinary Windows PowerShell:**

```powershell
$wslId = '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'
Get-NetFirewallHyperVVMSetting -PolicyStore ActiveStore -Name $wslId |
    Select-Object Name,Enabled,DefaultInboundAction,LoopbackEnabled,AllowHostPolicyMerge
Get-NetFirewallHyperVRule -VMCreatorId $wslId |
    Where-Object { $_.Direction -eq 'Inbound' } |
    Select-Object DisplayName,Enabled,Action,Protocol,LocalPorts,RemoteAddresses
```

These `Get-` cmdlets do not change firewall policy. If PowerShell cannot read the Hyper-V policy without administrator permissions, rerun them from an elevated PowerShell session; do not substitute `Set-` or `New-` configuration operations. The above WSL creator GUID is documented by Microsoft: https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall. Empty rule output does not by itself mean blocked; compare against effective `DefaultInboundAction`.

Windows firewall active profiles, IPv4 NAT/router port forwarding, IPv6 public routing, and VPN interfaces are separate acceptance gates. Don't disable a working firewall or expose the manager publicly just to prove reachability. R3 remains hard Off and publisher receipt/no-duplicate evidence remains open.

---

## G2.5 diagnostic: Windows listener and portproxy absence with working WSL/LAN dashboard (2026-10-31)

**Owner observed:** Windows PowerShell `Get-NetTCPConnection -State Listen -LocalPort 18790` produced no Windows listener result, while `netsh interface portproxy show all` had no entries. Both Windows LAN clients nevertheless continued to access Activity Manager after reboot, and OpenClawLab G2 postcheck had independently verified authenticated internal HTTPS and R3 hard Off. The Windows-only probes cannot enumerate all Linux-owned WSL sockets and do not establish absence of inbound LAN or WAN reachability. In mirrored WSL mode, a Linux service may be exposed directly through the host networking stack and relevant Hyper-V firewall policy. Microsoft documentation: https://learn.microsoft.com/en-us/windows/wsl/networking and https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/hyper-v-firewall .

**Corrected read-only commands from normal Windows PowerShell (do not add proxy or firewall entries):**

```powershell
wsl.exe -d OpenClawLab -u openclaw -- ss -lnt '( sport = :18790 )'
Select-String -Path "$env:USERPROFILE\.wslconfig" -Pattern '^\s*networkingMode\s*=' -ErrorAction SilentlyContinue
```

The first probes Linux listening addresses. The second reveals only an explicitly configured networking mode; no match is an inconclusive configuration hint, not proof the runtime uses NAT/mirrored. After those results, review **read-only** Hyper-V firewall WSL VM settings/rules, ordinary Windows firewall and router forwarding/WAN reachability. Avoid displaying full networking config or credentials. LAN reachability is already confirmed; no source/service/Windows changes are needed to fix this initial diagnostic mismatch. Separate external Moltbook receipt reconciliation remains open.

---

## G2.4 observed Activity Manager reachability from both Windows clients (2026-10-31)

After G2.3 verified OMEN Windows-logon WSL recovery, an active OpenClaw Gateway and passing local installed HTTPS/R3 Off checks, the owner reported that **both Windows computers successfully access the dashboard**. This completes the two-LAN-client reachability check. The report does not explicitly confirm fresh rotated-password login, a warning-free certificate indicator, or the absence of browser bypass; do not attribute those unreported observations.

Outstanding G2 acceptance: (1) independently reconcile original legacy publisher queue/attempted receipts with external Moltbook replies and any recorded target IDs; unchanged 23 attempted/0 uncertain counts are not comprehensive external duplicate proof, and (2) inspect Windows/WSL listener exposure, firewall and portproxy settings plus router forwarding to substantiate the private-LAN-only access requirement. Do not enable, stop or restart publishing services or alter Windows/WSL configuration as a test. Preserve R3 hard-Off.

---

## G2.3 supervised Windows reboot recovered core Bob services (2026-10-31)

**Actual owner-observed G2.3 recovery:** The OMEN Windows reboot was performed after a clean G2 preflight. Pre-reboot host gate passed with 23 historically attempted and 0 uncertain legacy publication jobs, user linger yes, reviewed publisher and current TLS/R3 Off state. After Windows sign-in, Windows PowerShell `wsl.exe --list --verbose` showed **OpenClawLab Running**, while Ubuntu and Ubuntu-24.04 were Stopped and docker-desktop Running. In the recovered OpenClawLab distro, `python3 scripts/report_g2_recovery.py --postcheck` returned `host gate: PASS`, installed HTTPS/R3 Off PASS, expected user service/timer and inert competing scope checks PASS, reviewed publisher, migrated SQLite journal/history verified, 23 attempted / 0 uncertain and linger=yes. `systemctl --user is-active openclaw-gateway.service` returned **active**. These findings verify the core Windows-interactive-logon to WSL/service recovery path at this time; they don't independently prove which exact Windows shortcut fired, pre-login unattended boot, remote browser trust, WAN isolation, or any external no-duplicate posts.

**G2 final acceptance still pending**, without another reboot or installation:
- From the OMEN and second LAN Windows computer, freshly authenticate at `https://192.168.1.24:18790/r3` with the rotated password. Confirm no browser certificate warnings or plaintext fallback. A CA-verified loopback check already passed, but real LAN clients need independent acceptance.
- Independently compare legacy `publish_jobs` attempts/uncertain states with actual Moltbook published comments/receipts or available remote identifiers around the reboot, treating unknown outcomes as review-only and never retrying blindly. The 23/0 counts unchanged across reboot mean no *new recorded local attempts* in that interval, not conclusive proof of external no-duplicate effects.
- Review Windows listening/firewall/port forwarding and router rules to substantiate LAN-only exposure. No public internet-facing dashboard is authorized.
- Preserve the existing user systemd publisher and Scout timers, inactive system-scope Scout timer, R3 hard-Off source, private queue and credential storage. No publisher oneshots, DB restoration, new send permissions or shortcut modifications to speed the check.

The `report_g2_recovery.py` script intentionally prints `Windows reboot observed by report: NO` and `External duplicate posting ruled out by report: NO`: the owner-reported event and external receipt review are distinct evidence that the script cannot generate.

---

## G2.2 Windows logon startup inventory accepted; G2.3 recovery runbook (2026-10-31)

**Owner-reported exact G2.2 Windows PowerShell output:** 0 relevant Scheduled Tasks, 0 Run registry matches, 2 **user** Startup-folder shortcuts, 0 query warnings. `Bob OpenClaw Startup` is a PowerShell shortcut; the local script was inspected and reports `wrapper-wsl=True`, `wrapper-distro=True`, `wrapper-systemd=True`. `OpenClaw Companion` is a second OpenClaw-named executable shortcut with no wrapper script. The collector wrote only a private report to user-local `BobBaseline` and changed no Windows startup configuration. This is **startup-discovery PASS**, not execution proof. Windows Startup-folder entries normally activate at interactive sign-in, not before Windows user login. `Linger=yes` is relevant only after WSL has already been started.

**Next G2.3: owner-supervised full Windows restart and same-user sign-in.** Do not run this test on a machine needed for active work. No new scripts, privileges, timers, services or startup triggers are necessary.

1. **Before restarting**, run from the existing `openclaw` WSL shell:
   ```bash
   cd ~/bob-next
   python3 scripts/report_g2_recovery.py --baseline
   ```
   Confirm host gate `PASS`; record attempted and uncertain job counts and R3 Off. Check new-password trusted HTTPS from both Windows computers. No credentials in logs.
2. **Owner manually restarts Windows** using the normal Windows Restart UI. Sign in to the same Windows account containing the two user Startup shortcuts. Do not open an OpenClawLab shell, start an OpenClaw service, or execute a WSL command that launches a distro until the next observation.
3. **Before manually launching WSL**, attempt Activity Manager login from the second LAN Windows computer at `https://192.168.1.24:18790/r3`, with the new Basic-auth credential and no browser trust warning. On the OMEN, use ordinary Windows PowerShell:
   ```powershell
   wsl.exe --list --verbose
   ```
   Observe whether OpenClawLab is **Running**. This is a list-only query and should not launch the distro. If **Stopped** or remote HTTPS is unavailable, save that observation; starting WSL to "fix" it would defeat the spontaneous-startup test. Do not edit Windows shortcuts until the finding is reviewed.
4. **Only if OpenClawLab was already Running**, enter the normal user `openclaw` WSL shell and run:
   ```bash
   cd ~/bob-next
   python3 scripts/report_g2_recovery.py --postcheck
   systemctl --user is-active openclaw-gateway.service
   ```
   Confirm G2 host gate `PASS`, Gateway `active`, all expected legacy user units/timers, competing system Scout and R3 candidate publisher inert, installed HTTPS and R3 hard Off. Confirm both Windows browsers reconnect to HTTPS without certificate warning or old-password acceptance. The G2 script's `Windows reboot observed: NO` and `External duplicate posting ruled out: NO` lines remain **intentional** even after a real restart: it cannot witness Windows reboot or external Moltbook state.
5. **Separate post-reboot interpretation:** compare old and new attempted/uncertain job counts with the installed legacy publisher's *actual timed activity* and external receipt/post history. Expected normal timer activity may legitimately advance the counters; unchanged counts alone cannot exclude external duplicates. Check the Windows LAN perimeter/WAN forwarding independently before claiming network isolation. No manually triggered publisher service, changes to source-Off R3, or SQLite restoration to investigate an inconsistent result.

**Current accepted milestones:** G2.1 read-only Linux baseline PASS; G2.2 Windows startup discovery PASS; actual owner reboot, remote TLS restoration, Gateway status and external no-duplicate verification remain OPEN.

---

## G2.1 host-state PASS and G2.2 Windows startup read-only gate (2026-10-31)

Latest operator-supplied G2 `python3 scripts/report_g2_recovery.py --baseline`: `host gate: PASS`; installed HTTPS/R3 compiled Off PASS; required user services and competing installed scope states PASS; original effective publisher reviewed; SQLite schema/migration journal verified; historical attempted jobs **23**, uncertain **0**; Linux user linger yes. The G2.1 correction only treats the system Scout's `loaded/inactive/static` service as inert when its paired installed **system timer is disabled and inactive**; no host service was modified. This is a baseline snapshot, not proof that Windows was rebooted or that external posts are non-duplicated.

**Next G2.2 Windows task (read-only startup inspection, before any planned reboot):** In ordinary **Windows PowerShell** on the OMEN, run the existing checked-in script via Windows-local temp file. It will generate one PRIVATE report under `%LOCALAPPDATA%\BobBaseline`, but not change Windows startup configuration.

```powershell
$script = Join-Path $env:TEMP 'bob-g2-windows-startup-review.ps1'
wsl.exe -d OpenClawLab -u openclaw -- cat /home/openclaw/bob-next/scripts/inventory_windows_startup.ps1 | Set-Content -Encoding UTF8 -Path $script
if ($LASTEXITCODE -ne 0) { throw 'Windows startup collector transfer failed' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script
if ($LASTEXITCODE -ne 0) { throw 'Windows startup collector refused or failed' }
```

Review only the sanitized **console** categories (number and trigger types of relevant tasks, Run keys, and user/machine Startup folder shortcuts; whether the known PowerShell wrapper mentions WSL/OpenClawLab/systemd; query warnings). Do not paste raw launcher arguments, underlying shortcut targets, credentials, or the private report into a public GitHub issue. The script doesn't inspect every possible Windows startup mechanism and does not prove execution, network reachability, or boot before logon.

Earlier observation: 0 matching scheduled tasks, 0 Run entries, 2 **user Startup-folder** shortcuts; `Bob OpenClaw Startup` references a PowerShell wrapper containing WSL/OpenClawLab/systemd markers; `OpenClaw Companion` launches an OpenClaw-named executable. Windows Startup-folder shortcuts normally run on **interactive logon**, not on power-on before someone signs in. Therefore G2 must explicitly test recovery **after signing in**, separately from any intended unattended boot behavior. A running WSL user systemd manager with linger=yes cannot boot WSL on its own.

**Do not reboot yet.** Once the new Windows audit is reviewed, decide separately whether to perform an owner-controlled Windows reboot/logon test and collect a postcheck. Keep current user/system Scout scope inertness, publisher attempt/uncertain history, two LAN HTTPS clients, LAN-only exposure evidence and external ledger receipts as independent acceptance gates.

---

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
