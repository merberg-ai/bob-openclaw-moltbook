# v0.7.1 integrated transaction recovery (isolated acceptance)

This increment combines the previously tested journal lock, pinned two-file release staging, real 127.0.0.1 fixture health checks, and synthetic SQLite write preservation into one transaction. It is **NOT a production installer**: no systemd, live manager, private database, or Moltbook request is contacted.

## Operator acceptance

Run on OMEN from PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && for scenario in healthy failed-health failed-recovery interrupt-before-switch interrupt-after-switch; do python3 scripts/rehearse_v071_integrated_recovery.py --scenario \"\$scenario\" || exit 1; done"
```

Expected: **191 tests** (previous 184 plus seven), subject to host verification, then five `v0.7.1 INTEGRATED RECOVERY: PASS` reports.

The five scenarios must produce these outcomes:

| Scenario | Outcome | Selected release | Journal phase |
| --- | --- | --- | --- |
| healthy | candidate_healthy | candidate | complete |
| failed-health | rolled_back | baseline | complete |
| failed-recovery | recovery_failed | baseline | incident |
| interrupt-before-switch | interrupted | baseline | prepared |
| interrupt-after-switch | interrupted | candidate | candidate_selected |

Interruption is injected deterministically, not created using real signals or process crashes. It leaves an **incomplete journal**, which the rehearsal reports for manual review, not automatic resumption. A failed recovery reports an incident rather than healthy status. The synthetic database preserves committed writes in every scenario.

**Limitations:** The HTTP adapter serves a disposable fixture, not Bob's generated manager; this isn't a real systemd restart or crash-consistency test. There is no live deployment mode. We still need process-crash recovery policy, health-auth acceptance, and a separate, explicit authorization before updating the actual service. Review ZIP remains non-deployable.
