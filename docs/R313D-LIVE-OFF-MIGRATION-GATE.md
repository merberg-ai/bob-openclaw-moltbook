# R3.13d owner-controlled live Off-schema migration gate

**Read-only by default. The live migration is not authorized or performed by merging this source.** The only supported writable operation is an explicit owner TTY-confirmed `--apply-off` once the *separately approved* Off-first release `v0.8.0-r3stage1` has been installed, the publisher timer and all relevant units drained, the global private pause marker present, and an independently restore-tested private SQLite backup created.

This is not a Bob R3 publisher activation or Moltbook canary, and **the three source-level publisher Off gates remain Off**. `releases/current.json` on `next` is now promoted to code-only `v0.8.0-r3stage1`; the installed host stays at Shadow4 until separately confirmed by the owner. Promotion alone does not migrate live SQLite. Neither the updater nor the ordinary Bob dashboard is allowed to migrate the live database implicitly.

## Code and operator boundary

The pure additive `src/bob_v08/r313d_live_off_contract.py` transaction creates only four R3.5 tables plus `r313c_action_envelopes` and versioned `r313c_schema_meta`, inserts four new **explicit Off** independent owner settings, and preserves every previously existing row in the five legacy tables. It refuses unknown/partial/future R3 schema or preexisting enabled R3 consent, and uses `BEGIN IMMEDIATE` so a pre-commit crash rolls the entire schema change back. Reapplying the exact Off schema does not reset a later uncertain send or delete a recorded attempt.

`scripts/r313d_live_off_migration.py` is the only live host command. By default it performs an **read-only** review of the fixed home/queue, installed publisher's reviewed effective unit and updater registry hash, all source hard-Off checks, the exact installed `v0.8.0-r3stage1` release/file hashes, and SQLite schema/owner settings. No paths, unit names, schema SQL, credentials or arbitrary host targets are accepted from CLI. It refuses root and does not expose token values, old comment bodies or unit contents.

The explicit `--apply-off` operation requires ALL of the following:

- The real Off-first release installed and registry-verified. It is **not** made active merely by the source PR or by invoking the updater. Source-staged candidates stay noncurrent until independent owner approval.
- The existing private `~/.config/bob-system/paused` marker in place, owned by the OpenClawLab account with restrictive permissions.
- The existing `bob-moltbook-publisher.timer` **disabled or masked and inactive**, its service **inactive**, and `bob-activity-manager.service` **inactive**. No second publisher, dashboard writer or new worker may be started during migration. The gate checks these read-only; it never stops or disables a service itself.
- No previous migration journal or simultaneous updater transaction; a private exclusive updater lock is held during backup and migration.
- A consistent SQLite online backup (including committed WAL) created in the existing private backup directory and **restored/tested** before touching the production queue. The backup is **not** uploaded or printed and is not automatically restored on rollback.
- An interactive owner confirmation typed exactly `MIGRATE R3 OFF` after the operation has been reviewed. No noninteractive, model-triggered or remote HTTP command can invoke the live migration without an interactive terminal.
- An atomic `BEGIN IMMEDIATE` schema transaction that inserts only reviewed tables/settings; preserves all old published, attempted, uncertain, approval, reply and event history; verifies the completed additive schema and the four explicit Off settings; writes a durable journal `prepared` then `complete`. A `prepared` journal after a crash is a **manual-inspection blocker**, never a prompt for blind retry or stale backup restoration.

## After stage1 source promotion

Complete the [explicit code-only stage1 installation](R313D-STAGE1-INSTALL.md) first. The read-only `report_r313d_stage1_installed.py` output must PASS before any separate maintenance-window schema work. **Do not run `--apply-off`** after a mere `bobctl update --check` or unverified code installation.

## Read-only verification after source promotion

The pre-promotion `report_r313d_off_first.py` report is a historical acceptance record and expects Shadow4 as the current manifest. After promotion, the supported read-only check is:

```bash
cd ~/bob-next && git pull --ff-only && bobctl update --check
```

Verify the expected stage1 release and seven code files before typed installation. The separate schema tool can also be inspected safely, without any writes:

```bash
python3 scripts/r313d_live_off_migration.py
```

Until stage1 installation, its output should report `installed Off-first release: not_verified` and `eligible for explicit migration: no`. **Do not run `--apply-off`** here. See the stage1 install SOP for the owner-confirmed code update.

## Actual production sequence still requiring distinct owner decisions

1. The reviewed stage1 manifest is now promoted on `next`. The owner must separately confirm and install the exact seven-file release using the established guarded updater, then pass the read-only installed acceptance report. The release **must not replace the existing credentialed publisher**, must have rollback-safe manager startup, and must retain the R2 Shadow4 features.
2. Enter a separately approved maintenance window, put Bob's publication workers on pause, drain/disable the existing publisher timer, stop publisher and manager services, and confirm the live Off migration preflight. Only then may the owner explicitly run the interactive `--apply-off`.
3. Independently verify the live migrated schema and default-Off settings, then restart the exact previous services and test UI/worker operation. **Rollback code and units only. Never restore an older SQLite database over later attempted/uncertain work.**
4. A *different* release would then need a separate owner-approved exact Bob draft and post-target canary, verified public target/author, final friend/owner/pause/budget checks, one credentialed publisher, no retry of unknown outcomes, and Windows/WSL reboot acceptance. This stage does not turn any real R3 dispatch switch On. R3 automatic publishing remains Off.

**No live migration, publisher service action, Moltbook write, credential access or production cutover was performed by this source-only branch.**
