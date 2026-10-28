# v0.7.0: Read-only systemd stage-execution preflight

**Status:** No service-manager execution is authorized by this phase. No unit is installed, registered, enabled, started, stopped, or restarted.

## Existing host acceptance

On 2026-10-28 the operator passed **99 local Python tests**, the inert Gateway crash/restart and release-rollback exercise (7 children reaped), and a SHA-verified audit of 15 installed unit files. The Gateway contained one unrecognized `[Service]` directive; the value-free audit classified its name as `other`. This does not establish whether it is harmless or supported by the installed systemd version. The original private unit values remain on the host.

## Purpose of the new preflight

`scripts/preflight_stage_systemd_manager.py` performs only **read-only** `systemctl show` queries. It checks user-systemd manager reachability, existence of required CLI programs, and collisions/reserved names in **both user and system scopes** for exactly ten hardcoded `bob-v070-stage-*` mock service/timer names. These are different from installed production unit names.

A single existing, masked, inactive-but-loaded, or otherwise reserved name blocks future stage execution review. Unavailable systemd queries and missing tools also fail closed. Unit contents, API calls, environment variables, credentials, installed configuration and private SQLite are not read or modified. Output is a small boolean/count summary.

**Pass is not authorization to execute mock units under the live user manager.** It does not prove cgroup/BPF networking restrictions, D-Bus isolation, port isolation, restart timing, worker drain, security boundaries, or a Windows cold boot. Any future transient execution will require a separate, operator-reviewed action plan with explicit approval and cleanup protections.

## OMEN command (PowerShell)

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "set -euo pipefail; cd ~/bob-v070-inventory; GIT_TERMINAL_PROMPT=0 git pull --ff-only; python3 -m unittest discover -s tests -p 'test_*.py' -q; python3 scripts/preflight_stage_systemd_manager.py"
if ($LASTEXITCODE -ne 0) { throw 'Read-only systemd stage preflight refused' }
```

Expected test count at this revision: **106**. The `SYSTEMD STAGING PREFLIGHT` result may be PASS or NOT READY depending on actual host configuration; do not alter the host to force a pass. Share only its sanitized console summary.

The next step, if the operator and future safety reviews approve it, is to plan a **single explicitly named transient mock service** with enforced network denial, verified process cleanup and no persistent unit files. That step is not implemented here.
