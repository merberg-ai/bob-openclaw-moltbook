# v0.7.1 final consolidated executor acceptance

The production-executor code paths are now tested **directly** through `tests/test_v071_final_executor_acceptance.py`. These tests redirect the production module's manager, navigation, and journal paths to private ephemeral directories, and replace real systemd commands and HTTP checks with deterministic in-process results. Scenarios cover successful install, health-failure rollback, failed baseline restart yielding an incident, interrupted file-install recovery, tamper refusal and recovery refusal when there is no journal. This does not create transient systemd units or connect to production.

## One operator acceptance

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/deploy_v071_activity_manager.py && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/v071_release_gate.py --backup /home/openclaw/.local/state/bob-baseline/backups/bob-activity-20261029T000527374127Z-170034.sqlite3 --skip-regressions"
```

The backup must still meet the 24-hour freshness limit. Tests should now number **284** (278 prior including the one new recovery test plus six final executor tests), subject to host verification. The release-gate step is read-only.

**This is not live-deployment approval.** Before `--apply`, the release executor should undergo additional scrutiny for unexpected filesystem layouts, torn writes, stale journals, auth and unit drift, and recovery exceptions. Only an explicit separate operator command can install.

The recurrent `READ-ONLY UI PREVIEW REFUSED` checkout warning is still unresolved. Distinguish that warning from the standalone candidate systemd acceptance, which previously passed.
