# v0.7.2 Job Tracking: release candidate

**Status:** Implemented in the GitHub development branch. **NOT YET INSTALLED** on the OpenClawLab host. Owner-reported current production has working v0.7.2 responsive Settings and 15-second System Status refresh.

## Actual worker stages

- Scout: queued, fetching discussions, validating selected feed, generating with OpenClaw, validating model reply, completed or failed.
- Original draft: queued, waiting for Gateway/Docker, generating with OpenClaw, validating draft, completed or failed. The SQLite `original_requests` table remains authoritative for its request state, completion timestamp, and error existence.
- Comment publisher: validating exact draft and approval, waiting for posting limits or pause, checking public target, sending, awaiting manual verification, verifying, completed, uncertain. The existing `publish_jobs` SQLite state is authoritative; failures that may have reached Moltbook **remain non-retriable automatically**.
- Original post publishing: existing `original_posts` SQLite states remain authoritative. This release does not change its posting or verification decisions. Worker checkpoints currently cover *original draft generation*, not detailed original-post HTTP substeps.

Each worker writes at most its current checkpoint to an owner-private `~/.config/moltbook/job-progress/<worker>.json` with fixed, non-sensitive stage labels and an ISO timestamp. Malformed/unsafe stage updates are discarded without disrupting worker behavior. Stale active stages become `unknown` rather than fake indefinitely active spinners.

System Status shows these stage cards and canonical latest 30 queue records, including creation and update timestamps, a Boolean error-recorded flag (never raw errors), and **no automatic retry**. The in-place 15-second refresh does not write to the queue. No percentage progress is claimed.

## Scope and security

No database migration, new publisher endpoint, automatic retry, secret read, approval change, scheduling change, or remotely executable job control. Existing comment/publication daily limits, explicit authorizations, original-post verification and cautious uncertain-result policies remain unchanged. Canceled comments and failing original-thought generation are pre-existing observed problems; this update makes their stages easier to diagnose, but does not claim to repair either.

## One focused staging check (read-only)

From Windows PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "set -e; cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile src/lib/bob/bob_job_tracking.py src/lib/bob/bob_live_status.py src/lib/bob/bob_status_view.py src/bin/bob-moltbook-scout src/bin/bob-moltbook-publisher src/bin/bob-original-worker scripts/patch_v072_job_tracking.py && python3 -m unittest discover -s tests -p 'test_v072_job_tracking.py' -q && python3 scripts/patch_v072_job_tracking.py"
```

No full-suite repeat is required. Readiness should print `v0.7.2 TRACKING READINESS: PASS`. The updater verifies installed manager and old worker/status byte hashes against `release_baselines/v072-tracking`. Any local drift results in a refusal, not an overwrite.

## Production update (requires fresh explicit approval)

After the focused check passes, an owner-approved update uses `python3 scripts/patch_v072_job_tracking.py --apply --confirm UPGRADE-BOB-JOB-TRACKING`. That takes and restore-tests a private SQLite backup, journals original code privately, installs the tracking module and five updated code files, restarts **only** the Activity Manager to load updated status modules, verifies authenticated HTTP and the presence of the new worker UI, and attempts code rollback if health checks fail. One-shot scout and publisher jobs will load their newly installed code on their next launch; currently running worker processes are not terminated or restarted. If the updater reports REFUSED or rolled_back, stop, do not immediately retry. An interrupted nonterminal transaction has `--recover --confirm RECOVER-BOB-JOB-TRACKING`, which validates the sealed baseline before any restoration.

This remains a version-pinned incremental release, **not** an automatic `git pull` deployment. A generic `bobctl update` will be a separate, future workflow.
