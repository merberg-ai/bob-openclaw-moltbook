# v0.7.2 Live Status UI, next small release

The owner's console login reset and responsive Settings style hotfix were successfully applied to the production v0.7.2 dashboard. These are the baseline for the **next** status-only update. The status patch has been committed to GitHub but **not deployed**.

## New behavior

- System Status displays readable service cards and the last 30 observed local queue entries.
- Scout/publisher one-shot services show `idle` when inactive between timer firings, not an alarmist `failed`. A real systemd failed state is labeled `failed`.
- Ollama readiness checks that Bob's configured `qwen3.5:9b` model is listed, not merely that the API responds.
- Status updates in place every 15 seconds while the page is visible, or via Refresh now. There is no full-page timer refresh; browser menu and scroll position remain intact.
- New status JS is a same-origin, authenticated, read-only asset at `/assets/bob-status.js`. Only the System Status page receives the narrowly scoped CSP permissions `script-src 'self'; connect-src 'self'`. All other routes retain the previous restrictive CSP. JSON is rendered with `textContent`, never `innerHTML`. No forms, workers, publishing states or credentials are mutated.

## Safe delivery workflow

The feature-specific updater is `scripts/patch_v072_live_status.py`. It refuses any installed code that differs from the exact reviewed post-Settings-hotfix v0.7.2 release. `release_baselines/v072/bob_live_status.py` preserves the original deployed status module bytes for exact comparisons.

The default invocation is read-only, does not restart Bob, and does not run the entire test suite:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/build_v072_live_candidate.py scripts/patch_v072_live_status.py && python3 scripts/patch_v072_live_status.py"
```

Expected: `v0.7.2 LIVE STATUS READINESS: PASS`.

Only after **separate, explicit production approval**, the operator can run `python3 scripts/patch_v072_live_status.py --apply --confirm UPGRADE-BOB-LIVE-STATUS`. This applies the manager, status backend and new status renderer only; takes a fresh verified SQLite backup first, records a private journal and old code, restarts only the manager, checks authenticated HTTP plus the JS asset, and rolls back code on failure. Interrupted transactions have a separate `--recover --confirm RECOVER-BOB-LIVE-STATUS` mode that refuses terminal journals.

This is a UI/status upgrade, not a persistent job-progress engine. Existing SQLite states are displayed as recorded; no progress percentage is fabricated. Jobs that are not currently represented in queue state cannot yet show granular generation progress.

The production repository branch should eventually be renamed to a version-independent release branch; the historical `feature/v0.7.1-navigation` name currently contains v0.7.2 work and is misleading. Do not reset or alter running installations merely to rename it.
