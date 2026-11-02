# v0.7.1 transaction-safety lab (synthetic only)

Operator accepted the prior 168-test baseline and synthetic failed-health rollback. This increment adds a non-deployable rehearsal for transaction safety.

The new `scripts/rehearse_v071_transaction_safety.py` uses only a private temporary directory and fake service responses. It stores an fsync'd JSON phase journal using an atomic rename, obtains an exclusive non-blocking OS file lock, refuses a previous incomplete journal, and bounds each simulated transaction to at most two restarts and two health checks. It models healthy update, failed candidate health with recovery, and failed recovery producing an incident. No code path accesses the real manager, database, systemd, Moltbook, network, or API credentials.

## Host acceptance

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_transaction_safety.py --scenario healthy && python3 scripts/rehearse_v071_transaction_safety.py --scenario failed-health && python3 scripts/rehearse_v071_transaction_safety.py --scenario failed-recovery"
```

Expected test count: **177**, subject to host verification. Each of the three scenario commands should print `v0.7.1 TRANSACTION LAB: PASS`. Failed recovery deliberately returns an incident, not a success claim.

## Important limitations

This is a **transaction model**, not a production installer: it does not yet include process-aware real service control, authentic health probes, signal interruption recovery, journal transition enforcement, a safe live release path, or actual disk-crash acceptance. A failed or incomplete transaction is refused rather than automatically resumed. Production requires a separately reviewed and authorized adapter and operator recovery plan. The existing UI review ZIP remains `deployable: false`. Do not deploy it manually.
