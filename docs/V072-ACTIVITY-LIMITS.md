# Bob v0.7.2 Activity Limits

**Status:** Reviewed implementation on feature branch; **not installed on the owner’s running OpenClawLab host** until a versioned `bobctl update` completes. Depends on operator-verified `v0.7.2-compact1`.

## What this adds

The existing **Settings** entry becomes a small overview with **Users & Access** and **Activity Limits** sections. `/settings/users` retains the old password-change UI and the exact `/settings/password` authentication/rotation code. No account or credential migration is performed.

`/settings/activity-limits` allows the dashboard owner to adjust five **server-enforced** limits, with a mobile-friendly form. New values are validated by a strict integer allowlist, saved transactionally in the existing private `publish_settings` SQLite table, and recorded as a metadata-only event. The form requires valid CSRF/Origin, Basic auth, a bounded request body, and typed `APPLY LIMITS` confirmation. Settings do **not** toggle `auto_enabled`, approve drafts, change the publisher timer, or create a publication job.

| Name | Migration fallback before owner saves | Recommended preset | Allowed range |
| --- | ---: | ---: | ---: |
| Comment attempts per UTC day, all modes | 2 | **6** | 1–20 |
| Minimum spacing between comment attempts | 60 min | **45 min** | 10–180 min |
| Automatic comment attempts per UTC day (subset of total) | 2 | **3** | 0–20, never higher than total |
| Original-post attempts per UTC day | 1 | **2** | 1–5 |
| Minimum spacing between original-post attempts | 120 min | **120 min** | 30–360 min |

**The recommended values are NOT applied automatically by installing the release.** In the Activity Limits section, select **Load recommended**, inspect the fields, type `APPLY LIMITS`, and save. The new settings affect the **next eligible timer run**. Existing attempted sends are counted; changing the cap does not clear history, reset UTC windows, or post immediately.

## Worker enforcement and platform boundaries

- The comment publisher reads the shared **total** attempt count and a separate count of **automatic** attempts before its existing preflight and `sending` state transition; the spacing applies across both manual and auto comments.
- Manual approvals retain FIFO priority over auto drafts. A human-approved comment can use remaining total budget even after the auto budget is exhausted. Automatic comments still require the independent auto_enabled flag and freshness/integrity checks.
- The original-post worker independently reads its own daily attempt cap and spacing before recording `sending`. Original posts still require explicit owner approval and publication queueing.
- Existing `paused` mode, deduplication, challenge handling, no-silent-retry policy and pre-POST intent persistence remain unchanged. An uncertain result counts as an attempt.
- Missing setting values preserve the historic safe defaults. **Corrupt, unsupported, or out-of-range persisted settings refuse worker sends** rather than granting unlimited capacity.
- Moltbook's documented platform limits and 429 responses always remain authoritative; new agents can have stricter limits. Bob does not automatically retry ambiguous writes, including a 429. See [Moltbook official skill documentation](https://www.moltbook.com/skill.md).
- Increasing budgets does not increase the number of **scheduled timer wakeups**; actual cadence is also bounded by installed systemd timers and availability of approved/fresh drafts.

## Release and tests

`v0.7.2-activity-limits1` has exactly five live files: `bob_activity_limits.py`, `bob_dashboard_compact.py`, `bob-moltbook-publisher`, `bob-original-worker`, and `bob-activity-manager` (built from the pinned current candidate). The updater backs up SQLite before installation, swaps each file atomically, restarts **only Activity Manager**, checks authenticated health and rolls back if necessary. Existing running one-shot workers complete their invocation with the old code; subsequent executions load the new shared policy module.

Focused offline coverage includes fallback defaults, validated recommended caps, auto/manual sub-budgets, original spacing, invalid persisted settings, read-only preset preview, credential preservation and exact unchanged sensitive dashboard routes. Production deployment and real Moltbook publication are not invoked by the test suite.

## Operator rollout

1. Verify `bobctl update --check` reports `v0.7.2-activity-limits1` from `v0.7.2-compact1`.
2. Run `bobctl update`, read the five-file list, and type `UPDATE`.
3. Open `/settings`, then `Users & Access` and `Activity Limits`. Confirm existing login/password change and current default caps.
4. Load the recommended preset, type `APPLY LIMITS`, save, and confirm the stored values and today’s attempt counts.
5. Read the activity overview after the next ordinary worker run. **Do not manually invoke publisher-run merely to test a UI change**; that command can trigger a real post.

The safe installer and release process are separate from the still-unimplemented clean Windows/WSL installer.
