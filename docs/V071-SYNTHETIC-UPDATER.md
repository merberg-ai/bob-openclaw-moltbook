# v0.7.1 synthetic update lifecycle (NOT DEPLOYABLE)

Following operator acceptance of 163 regression tests and isolated HTTP runtime, this milestone introduces `scripts/plan_v071_update.py`. It models five service-release outcomes against **temporary fake release directories**. It does not perform production preflight, backup, installation, service restart, HTTP requests, credential access or live database operations. No option enables those actions.

## OMEN acceptance command

Run from Windows PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && for scenario in success failed-health failed-recovery pre-switch restart-failure; do python3 scripts/plan_v071_update.py --scenario \"\$scenario\" || exit; done"
```

The regression suite now includes five additional state-machine tests (expected total **168**, subject to host verification). Each synthetic scenario should print `acceptance: PASS`. `failed-recovery` intentionally ends in a simulated failed state and must never be described as restored.

## Exact security boundary

- Candidate source is regenerated from the SHA-pinned baseline and reviewed two-file archive.
- Versioned baseline and candidate are stored only in a private temporary directory; the active link switches there.
- Service restart and health outcomes are **injected booleans**, not real systemd actions or real HTTP health checks.
- On simulated failure the prior code pointer is restored, then simulated recovery state is evaluated.
- An interrupted live update, service drop-ins and direct `ExecStart` path remain unhandled and MUST NOT be inferred safe from this model.
- Existing release ZIP remains `deployable: false`. Explicit production approval is still required.

Next engineering gate: design a durable journal/lock and a clearly separated synthetic service adapter with bounded health checks. Only after those tests and service-launch contract review can an operator-approved live updater be considered.
