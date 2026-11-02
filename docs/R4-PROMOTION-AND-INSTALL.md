# R4 autonomy1 manifest promotion and single-owner installation

**Source:** PR #138, merged to `next`. **Installed on OMEN:** `v0.8.0-autonomy1` by an explicitly owner-typed `UPDATE`, with independent installed acceptance **PASS** reported 2026-11-01 PDT. R4 social dispatch remains hard-Off.

## Installation outcome and browser acceptance

On 2026-11-01 PDT the owner provided the actual OpenClawLab terminal outcome:
`BOB UPDATE: updated`, followed by a separate
`report_r4_installed.py --check` response with `acceptance:PASS`,
`release:v0.8.0-autonomy1`, verified signed source and legacy/R3 registry,
authenticated HTTPS, new R4 routes, additive versioned schema, idle original
publisher, `new_r4_actions_attempted:0` and
`public_send_armed_by_report:false`. The acceptance *report* is read-only;
the earlier approved installer actually performed the additive schema migration.
These results are owner-provided evidence, not independently issued host probes.

**Remaining acceptance:** in the normal remote LAN browser, open
`https://192.168.1.24:18790/r4/now`, authenticate using the existing
Activity Manager credentials and visually inspect R4 Now, Inbox, Bob,
Controls and Diagnostics. Confirm the original R3/Scout/PM/FM navigation
still works and check mobile-width layout if practical. The inert Chat
placeholder is not yet a live agent conversation. Do not change Auto dials,
submit proposal/approval/social actions, restart timers or test Moltbook
network sends during the passive visual smoke.

## Release boundaries

- Source PR #137 was merged into `next` with all R4 social dispatch hard-Off.
- Owner-submitted actual OMEN read-only GO/NO-GO (2026-11-01 PDT): seven host checks true, zero blockers, 23 real candidate files verified, HTTPS and original publisher topology confirmed. This is a snapshot, **not installation permission**.
- Promotion PR #138 makes `releases/current.json` exactly match the separately reviewed `releases/candidates/r4-autonomy1-consolidated.json`. The release chain is `v0.8.0-r3canary1 → v0.8.0-autonomy1`, with 23 payloads and restart of the existing Activity Manager **only inside an owner-approved updater transaction**.
- The source and host reports verify the exact promoted manifest and repeat the owner/HTTPS/idle-publisher/journal checks before the one install. Missing evidence blocks install.
- No R4 public actions are enabled in this release. No new publisher service, new timers, R4 API credentials or public writer.

## One-time operator flow, after promotion PR merges and CI passes

**No commands in this section run automatically after merging a GitHub PR.**
Do not run an older installed updater: `bobctl update` currently uses a
legacy release transport table which does **not** recognize R4. Use the
source-reviewed `~/bob-next/scripts/bob_release_updater.py` instead.

Run as non-root `openclaw` in OpenClawLab, from the trusted clean `next`
checkout. At the exact installation step, the updater separately requires
typing **UPDATE** at a real terminal. A normal `--check` does not install
but can update the trusted Git checkout by fast-forward:

```bash
cd ~/bob-next && git pull --ff-only && PYTHONDONTWRITEBYTECODE=1 python3 scripts/report_r4_go_nogo.py --check && python3 scripts/bob_release_updater.py --check
```

Only after reviewing the real output and affirmatively deciding to install,
run this distinct operator command:

```bash
cd ~/bob-next && python3 scripts/bob_release_updater.py
```

Type `UPDATE` only for the reviewed `v0.8.0-autonomy1` release and
23 expected files, after the R3 original publisher is idle. The updated
script performs verified private SQLite backup and independent restore,
stages hash-verified candidate files, rechecks publisher topology, migrates
R4-only additive schema, restarts the existing HTTPS Activity Manager and
checks health. Any normal failed installation invokes **code/registry-only**
rollback; it NEVER restores stale SQLite over a new historical publication
attempt. Crashes may require the separately owner-confirmed `--recover`.
The completed-release fallback `--rollback-r4` is also owner-confirmed,
code/registry-only and separate from interrupted recovery.

### After install, read-only acceptance

```bash
cd ~/bob-next && python3 scripts/report_r4_installed.py --check
```

It checks the installed signed release, additive schema, inactive original
publisher, no attempted R4 sends, and authenticated CA HTTPS routes. Confirm
R4 pages also work from the normal LAN browser. An acceptance failure is a
reason to inspect, **not** to repeat an attempted public action, disable
timers or overwrite the database.

**Not part of this promotion:** real R4 upvotes, follows, comments, original
posts, automatic social modes, or a second publisher. A future signed
release and distinct explicit owner authorization will be required for any
R4 public social action.
