# R3.13d stage1 Off-first installation: owner-operated release

**Promoted release:** `v0.8.0-r3stage1`, source branch `next`. **This is a code-only release, not R3 cutover, not live database migration, and not permission to send new Bob-authored Moltbook comments.** The existing credentialed v0.7 publisher is not in the manifest. Real R3 dispatch stays protected by three reviewed hardcoded Off gates; automatic R3 publication remains compiled Off.

## Release contents

The exact reviewed manifest is `releases/current.json` and upgrades installed `v0.8.0-shadow4` to `v0.8.0-r3stage1`. The seven files are the separate R3 package, fixed proposal-only launcher, verified-package loader, independent R3 owner-controls library, authenticated R3 page, generated Activity Manager and generated navigation. No production DDL or owner settings are touched by the updater. The updater preserves all other installed files, including Shadow4, the existing credentialed publisher, its timer and the Gateway.

The package loader resolves Python's cached `bob_v08` Shadow4 namespace only after independently verifying **both the old Shadow4 archive and the new R3 archive** against the updater registry. This prevents a subtle but real missing-module failure in the running Activity Manager. The integration smoke uses an isolated synthetic HOME, both archives, a registry with test hashes, real loopback HTTP, synthetic LAN Basic auth, Origin/Host and CSRF checks; it asserts production account-boundary refusal before injecting a synthetic matching account.

## OMEN install, after the reviewed PR has merged into `next`

Run as the existing unprivileged `openclaw` user in the OpenClawLab WSL distro, with your updater configured for trusted `next`. **Do not use sudo**:

```bash
cd ~/bob-next && git pull --ff-only
bobctl update --check
```

Expected: `BOB UPDATE AVAILABLE: v0.8.0-r3stage1`, seven listed code files, `Restart Activity Manager: True`, and `CHECK ONLY`. The check changes no installed files, schema, owner controls, services or Moltbook state.

If the exact version and file list match, perform the explicitly confirmed code-only update:

```bash
bobctl update
```

At the install prompt, type `UPDATE`. The existing updater takes a restore-tested private SQLite backup, journals and installs the reviewed files, restarts only Activity Manager, checks authenticated existing routes, and rolls back **code only** if a startup/health check fails. **No database migration or database restore is part of this installation.** Never blindly retry a failed updater; inspect its journal and reported rollback outcome first. `BOB UPDATE: updated` is required before proceeding.

After a successful installation, run the single read-only acceptance report:

```bash
python3 scripts/report_r313d_stage1_installed.py
```

Expected:

```text
R3.13d OFF-FIRST STAGE1 INSTALLED (READ-ONLY)
installed release: verified
R3 real-send source gates: verified_off
authenticated R3 Controls: authenticated_read_only_page
installation acceptance: PASS
live database or services changed by check: NO
new public R3 posting rights: NONE
Moltbook canary authorized: NO
```

Also open `/r3` on the **existing authenticated Activity Manager LAN URL**. The Controls page should load and indicate that the R3 schema is not yet installed, so the owner controls remain read-only. The rest of the dashboard, Shadow Now/Inbox, Scout and legacy publisher must continue working.

## What the successful stage1 install does NOT authorize

The separate production schema migration is `scripts/r313d_live_off_migration.py`, **read-only by default**. Its write option is still blocked until the owner independently authorizes a maintenance window, pauses and drains the existing publisher and manager, confirms the backup/rollback plan, and types its separate `MIGRATE R3 OFF` phrase at a terminal. **Do not run `--apply-off` just because stage1 installed.** A later live R3 manual comment requires separate exact-post/exact-draft consent and new publisher cutover acceptance. Automatic R3 remains Off. R2 G1 natural scheduled fresh source-linked decision remains open.

If the installed report fails, do **not** advance to migration or real publishing. Record its sanitized output and investigate the installed registry, unit/HTTP health or rollback journal. No public Moltbook canary is part of stage1.

**Stage1 R3 public dispatch authorized: NO.**
