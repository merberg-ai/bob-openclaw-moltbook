# v0.7.0: Inert process lifecycle and Gateway unknown-key classification

Status: **developer-only offline rehearsal**, not live service-manager testing or an installable release.

## Host acceptance through previous phase

The OMEN passed 92 offline Python tests, static `systemd-analyze verify` for all 10 mock units, and a private SHA check of all 15 installed Bob/OpenClaw systemd files. The read-only audit found one unrecognized Gateway unit directive. No actual unit value or unknown directive name was disclosed.

## New stage: mock process supervision

`scripts/rehearse_inert_process_lifecycle.py` uses a fresh, auto-deleted private sandbox created by `stage_service_graph.py`. It launches only the trusted, fixed mock Gateway/Activity Manager actor under two private process sessions. The mock actor uses a private dummy-only configuration (publishing and network disabled), never contacts APIs, and records only role/release information into a synthetic SQLite database.

The test observes initial baseline starts, deliberately crashes the mock Gateway process group, starts it again, stops the mock processes, starts candidate mock services, then switches back and starts baseline mocks. All seven child processes are explicitly reaped, even on assertion failure. Nothing is installed, enabled, restarted or changed in live systemd. This is a **simulated supervisor test**, not proof of systemd's restart policy.

## Gateway directive classification

`audit_live_unit_directive_names.py` now emits one coarse, fixed family label per previously unknown directive. Examples include `restart`, `timeout`, `security` or `other`. It continues to hash-check exact installed source files against the private inventory, and it stores **no unknown directive name, command argument, environment value or path**. The count of unknown directives is unchanged.

An `other` result is not sufficient to reconstruct the directive; it means separate carefully reviewed local inspection is still needed. Do not guess missing original values or remove the directive.

## One Windows PowerShell paste

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "set -euo pipefail; cd ~/bob-v070-inventory; GIT_TERMINAL_PROMPT=0 git pull --ff-only; python3 -m unittest discover -s tests -p 'test_*.py' -q; python3 scripts/rehearse_inert_process_lifecycle.py; python3 scripts/audit_live_unit_directive_names.py --topology-report /home/openclaw/.local/state/bob-baseline/inventory-20261028T144113282656Z-93497.json"
if ($LASTEXITCODE -ne 0) { throw 'v0.7.0 mock lifecycle or Gateway audit failed' }
```

Expected at this revision: 99 Python tests, `INERT PROCESS LIFECYCLE: PASS`, seven mock starts, verified crash/restart and rollback, all mock children reaped; `PRIVATE DIRECTIVE-NAME AUDIT: PASS`, 15 hashed installed source files, and a value-free Gateway unknown-family classification.

Do not publish the private JSON audit, unit files or command arguments. Only share console status and coarse family categories. No production changes are authorized here.

Remaining release gates: actual isolated systemd manager execution, faithfully recreated and reviewed original unit settings, publish-job drain/uncertain-delivery handling, post-update health checks, and Windows cold-boot recovery.
