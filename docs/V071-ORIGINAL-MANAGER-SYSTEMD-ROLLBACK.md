# v0.7.1 original-manager systemd rollback rehearsal

This opt-in script launches **two real code versions** in sequence under uniquely named disposable user-systemd units: the generated v0.7.1 two-file manager and the unmodified, SHA-256-pinned v0.6 original manager. It uses a synthetic HOME and synthetic SQLite, binds only loopback on ephemeral ports, rejects POST, and touches no live Bob services, configuration, credentials or publishing.

A healthy scenario checks the candidate and stops it. The failed-health scenario **injects a failed verdict after candidate HTTP succeeds**, stops it, then loads and checks the **real original manager** under a separate temporary unit. This is not yet switching Bob's actual installed executable, nor is it an automatic rollback transaction journal. The candidate and baseline use the same synthetic HOME so committed synthetic data can survive service replacement.

## Gate A: regression and plan only

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_original_manager_rollback.py"
```

Expected **238 tests** (232 prior plus 6); host verification required. Plan must print `v0.7.1 ORIGINAL MANAGER ROLLBACK: PLAN ONLY`.

## Gate B: opt-in transient launch

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/rehearse_v071_original_manager_rollback.py --execute-transient --scenario healthy"
```

If healthy passes, exercise the injected rollback:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/rehearse_v071_original_manager_rollback.py --execute-transient --scenario failed-health"
```

Expected `v0.7.1 ORIGINAL MANAGER ROLLBACK: PASS` with `outcome: original_manager_recovered` for the second command. **Stop and investigate on REFUSED**; do not repeatedly retry when transient cleanup may have failed.

Remaining before a live release: durable rollback journal wired to the real installed source switch; systemd launch/path preservation; authenticated LAN health; service status and cleanup verification; fresh database backup; and separate production authorization.
