# R4 production-shaped rehearsal and release review

**Status:** source rehearsal in PR #137, **not an OMEN installation**. The trusted
`next` manifest remains `v0.8.0-r3canary1`. The separate candidate is
`releases/candidates/r4-autonomy1-consolidated.json`. No public R4 action is
authorized by this review.

## What the isolated rehearsal actually executes

`tests/test_r4_production_shape_rehearsal.py` builds all **23 real candidate
payloads** (including the generated HTTPS Manager) from the candidate manifest,
then exercises the existing updater's real `update()`, filesystem archive,
SHA-256 registry validation, real online SQLite backup and independent restore,
`r4_install_guard`, hash-verified installed schema module, transaction journal,
additive SQLite migration and `rollback()` against a disposable private tree.

The file-backed fixture includes an existing, recorded R3 public-canary comment
and R3 proposal. Acceptance checks:

1. Successful update: candidate hashes, code, exact HTTPS release binding,
   `complete` journal, complete empty R4 tables, no added public send, and
   unchanged legacy R3 publication receipt.
2. Failed candidate HTTPS **postflight**: host boundary deliberately fails after
   migration; updater automatically restores R3 code/registry, while preserving
   the new inert R4 tables and all existing historical records.
3. Process interruption **after `migrated` and before completed restart**:
   the `migrated` journal remains recoverable. Explicit code-only rollback
   restores R3 binaries/registry and **does not overwrite a later attempted
   publication record in SQLite**.

### What this does NOT prove

This is **not** a second publisher, a Windows/WSL install, a real systemd
migration or a live HTTPS socket test. Only the host service restart and
authenticated HTTPS health probes are mocked. No physical OMEN paths,
credentials, Moltbook API requests, or installed databases are used. The
existing independent R4 route/auth/CSRF and transport tests supplement this
fixture, but cannot replace an actual operator acceptance after deployment.

**Critical release boundary:** the installed R3 updater cannot identify the
new R4 release's HTTPS transport. A promoted, trusted, updated checkout must
run the reviewed `scripts/bob_release_updater.py` for this bridge install.
Do **not** use the old installed updater for R4, manually execute schema DDL,
run the rehearsal against the live database, or copy a SQLite backup over
newer publication attempts.

## Remaining release gates

- [ ] All PR checks on the final commit pass, including Windows checks.
- [ ] Review exact 23-file payload and four independent real-send Off markers.
- [ ] Verify one original publisher unit/timer, read-only effective unit
      inventory, and no new credentialed R4 service.
- [ ] Review the authenticated CA-verified HTTPS route behavior in an isolated
      service-shaped smoke; no fallback to HTTP or public listener.
- [ ] Document the post-`complete` rollback procedure separately. The updater's
      existing `--recover` only accepts interrupted journal phases; a completed
      release is **not** currently undone with `--recover`.
- [ ] Merge this source PR to `next` **only after** review. A distinct explicit
      release-promotion change to `releases/current.json` comes later.
- [ ] One owner-confirmed OMEN R4 install, then read-only
      `python3 scripts/report_r4_installed.py --check` and LAN browser smoke.
- [ ] Independent, subsequent owner decision and new signed release for any
      real R4 upvote/follow/comment/post path. **Installation alone grants no
      real R4 API sends.**

Do not request terminal commands from the operator until the source and
promotion gates are complete. All pending checks must be reported as pending,
not silently implied by passing Python unit tests.
