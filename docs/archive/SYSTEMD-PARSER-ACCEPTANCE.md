# v0.7.0: Static systemd parser and directive-name audit

Status: development-only acceptance. These are not deployable units.

## Local result

The operator passed 84 local tests, source rollback and the inert mock graph (6 services, 4 timers, 14 synthetic runs), without modifying the live installation.

## Next checks

The new value-free directive collector checks original installed unit SHA-256 against the private topology report. It saves only allowlisted directive *names* and counts to a private JSON report. Unknown/custom names and all directive values are omitted.

The new parser check passes freshly generated, staging-prefixed units to `systemd-analyze verify` in a temporary directory. It never registers, enables or starts these units. The mock graph is deleted afterward.

Run from Windows PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "set -euo pipefail; cd ~/bob-v070-inventory; GIT_TERMINAL_PROMPT=0 git pull --ff-only; python3 -m unittest discover -s tests -p 'test_*.py' -q; python3 scripts/verify_inert_stage_units.py; python3 scripts/audit_live_unit_directive_names.py --topology-report /home/openclaw/.local/state/bob-baseline/inventory-20261028T144113282656Z-93497.json"
if ($LASTEXITCODE -ne 0) { throw 'v0.7.0 staging parser or directive audit failed' }
```

Expected: 92 tests, `SYSTEMD INERT UNIT PARSE: PASS`, `PRIVATE DIRECTIVE-NAME AUDIT: PASS` and 15 SHA-verified installed files.

Do not share the private JSON report or raw unit bodies. The safe console output includes only known Gateway directive names and unknown counts.

Limitations: parser success verifies the synthetic units' syntax, not an actual service restart. Directive names do not supply the missing values. The actual live-unit behavior, service-manager recovery and unattended Windows boot are still unproven.
