# v0.7.2 Queue dashboard: failed update and guarded recovery

**Status:** Recovery and improved updater are committed to GitHub `main`; **not yet applied on the owner's OpenClawLab host**. No automatic Moltbook publications are authorized by this procedure.

## Observed incident

The operator attempted to install the first nonempty release `v0.7.2-queues1`, and `bobctl update` reported `REFUSED (ValueError)`. Read-only examination then showed:

- Installed registry: `v0.7.2-main-channel`, matching every registered live file hash.
- Saved transaction journal: `incident` for `v0.7.2-queues1`.
- Authenticated routes `/healthz`, `/settings`, `/activity`, `/system/status`, and `/api/system/status`: **all passed**.
- Old manager and navigation code: **baseline**; new `bob_dashboard_manage.py`: **absent**, exactly as before the attempted upgrade.
- Old transaction archive `~/.local/state/bob-updater/tx-v0.7.2-queues1`: intact.

**Cause:** The initial updater reported only the exception class; it did **not** record the failing stage, so an exact root cause cannot be established from this evidence. The improved updater adds a bounded post-restart readiness window and prints a safe failing stage on future rollbacks. Timing is a plausible cause, not a confirmed cause.

## One-time safe reconciliation

Run from the ordinary `openclaw` shell, **not root**:

```bash
cd ~/bob-main && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_queue_incident_repair_smoke.py' -q && python3 scripts/reconcile_bob_queues1_incident.py --apply --confirm RECONCILE-BOB-QUEUE-INCIDENT && bobctl update --check
```

The repair re-verifies the exact old updater checksum, all installed file hashes, archived source and candidate digests, the three restored application files, release-chain metadata, clean trusted Git `main` checkout, and authenticated dashboard health. It then makes **only** these local changes:

1. Replaces `~/.local/bin/bob-release-updater` with the code-reviewed, main-pinned version including bounded restart health checks.
2. Records its new SHA-256 hash in the private installed-release registry (the installed application release **remains** `v0.7.2-main-channel`).
3. Moves the original `incident` journal into a verified, explicitly reconciled `rolled_back` state. The **original failed transaction archive is preserved unchanged**.

The repair writes private snapshots of the original updater, registry, and journal before changing anything; an interrupted repair is recoverable from those snapshots with an explicitly confirmed recovery action. It never edits the Moltbook database, dashboard code, publishing queue, authorization state, or service units. It does **not** restart the dashboard or contact Moltbook.

Expected successful output includes:

```text
Ran 3 tests
OK
BOB QUEUE UPDATE REPAIR: baseline_reconciled_updater_patched
BOB UPDATE AVAILABLE: v0.7.2-queues1-r1
BOB UPDATE: CHECK ONLY; no production changes
```

`v0.7.2-queues1-r1` is a **new immutable release ID** with the same reviewed dashboard files, explicitly avoiding the already archived `v0.7.2-queues1` transaction directory. It does not reuse or delete the first transaction archive. **Do not rerun the repair after successful reconciliation.**

## Then install normally

Once the repair reports success and the normal updater advertises the new ID, run:

```bash
bobctl update
```

Review the exact three installed files and the proposed Activity Manager restart, then type `UPDATE`. The standard updater takes another verified online SQLite backup before code replacement, restarts only the Activity Manager and checks the authenticated dashboard. It does not start publisher/scout workers or submit network comments.

If either step reports `REFUSED`, `rolled_back` or `incident`, **stop and inspect**, rather than retrying or removing state files. For a genuinely interrupted **repair** only (not a completed one), see `--recover --confirm RESTORE-BOB-QUEUE-REPAIR` in `scripts/reconcile_bob_queues1_incident.py`; do not invoke it without examining the repair state.

The update is **not yet installed on the operator's machine**. Until confirmed, the old Activity Manager remains authoritative.
