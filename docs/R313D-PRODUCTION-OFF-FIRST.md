# R3.13d production code: Off-first owner controls and sealed Bob proposals

**Implementation candidate only. Do not claim live cutover, real posting, or installed owner controls.** The active updater manifest remains `v0.8.0-shadow4` and the installed legacy publisher remains the sole credentialed Moltbook writer.

## What is ready for source review

- A separately authenticated **Bob R3 Controls** route at `/r3` in Activity Manager. Its extension is isolated in `src/lib/bob/bob_r313d_web.py`; the original `src/bin/bob-activity-manager` v0.6 source hash remains unchanged. `scripts/build_r313d_manager_candidate.py` derives the full existing R2 Shadow/ FM4.1/ OC4 generated Activity Manager and adds one subclass, delegating all other GET/POST methods unchanged. The existing LAN Basic authentication, allowed Host, strict browser Origin, secret CSRF token and private fixed owner SQLite boundary apply to R3 actions too. No other sensitive routes change.
- Explicit typed `ENABLE R3 MANUAL` or `DISABLE R3` owner controls; no R3 rights are inferred from legacy Scout approvals or legacy `auto_enabled`. `R3_AUTO_UI_COMPILED_OFF=True` prohibits automatic Bob-authored comment publication regardless of owner settings or form submission. Every new Bob draft needs an **independent SHA-sealed approval**, and queueing the exact approved text requires separate typed `QUEUE BOB COMMENT` confirmation. Revocation cancels only **unattempted R3** queue jobs; existing legacy jobs and attempted/uncertain history are retained.
- A fixed local `bob-r3-propose --once` process invokes the real OpenClaw main Bob through his verified saved Scout observation, validates the strict five-field model decision, and stores a canonical envelope and proposal under a single SQLite `BEGIN IMMEDIATE`. A skipped response creates no comment. **No publish_jobs row, owner approval, API credential lookup, HTTP POST, new publisher or implicit auto queue** is ever created by this worker. Any R3 owner approval must be separately made from the dashboard.
- A deterministic, separate `bob_r3_package.pyz` with required R3 modules, compiled from reviewed source. Its local owner-reader uses the installed updater's **recorded SHA-256** and private regular-file/path checks before importing it. This package is independent of the Shadow4 package and activation pointer.
- An **Off-first release candidate** at `releases/candidates/r313d-off-first-owner-controls.json`, upgrade chain `v0.8.0-shadow4` to `v0.8.0-r3stage1`. The reviewed manifest installs *only* the new R3 package, proposal launcher, R3 owner modules, generated manager and navigation. It **does not replace the installed credentialed publisher**. The existing guarded updater's rollback changes only code, never rewinds SQLite history.
- A read-only report `scripts/report_r313d_off_first.py` which builds both candidate bundles in memory, requires the current active manifest to remain Shadow4, verifies all three hard-Off publisher source gates, and reuses the previously accepted OMEN trusted-host/publisher registry attestation. It has no install, DDL, service or network option.

## Operator check on OMEN after source merge

Run as the normal OpenClawLab user, not with sudo:

```bash
cd ~/bob-next && git pull --ff-only && python3 scripts/report_r313d_off_first.py
```

This is **read only**. A PASS is proof of source/build compatibility and a point-in-time installed host boundary, **not** permission to migrate the real DB or send a comment.

This checkpoint intentionally does not change `releases/current.json`; `bobctl update` is not the installation command until the independent Off-first release promotion has been reviewed and approved.

## Remaining explicit production approvals

The next deployment gate must separately promote the reviewed Off-first release and install through the existing authenticated guarded updater, while preserving the current legacy publisher and R2 shadow files. The R3 schema must then be migrated with verified offline maintenance boundaries, private restore-tested backup, transactional additive tables and default-Off settings, durable migration journal, and **code-only rollback without restoring stale database contents**. The dashboard will show R3 schema unavailable until then.

The manual-only credentialed publisher canary requires a **separate owner-approved release and an exact post/draft approval**, final source+author public GET, friend/owner/pause/rate final barrier, no concurrent second publisher, and a verified reboot/recovery. Unknown sends remain uncertain with no automatic retry. Automatic R3 posting stays Off until its own later explicit permission.

No real Moltbook post, live DDL, systemd control, credential read, or installed files were changed by this source-only candidate. R2 G1 natural fresh scheduled source-linked decision remains open.

**R3.13d production cutover authorized: NO.**
