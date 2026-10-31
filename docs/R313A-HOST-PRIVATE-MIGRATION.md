# R3.13a: trusted WSL host roots and disposable SQLite migration rehearsal

**Status: source-only / owner preflight, NOT an installable release.** The
existing v0.7 credentialed publisher remains installed, R3.12 real dispatch
stays hard Off, and no new R3 manual or automatic posting permission is granted.

## Fixed installed-host boundary

The R3.13a CLI accepts no arbitrary database, source, pause, service, token,
URL or model-proof arguments. Paths derive from the current WSL user's home
and the existing R3 inventory constants:

- Database: ~/.config/moltbook/activity-queue.sqlite3
- Saved Scout data: ~/.config/moltbook (metadata only, no raw Scout content)
- Global pause marker: ~/.config/bob-system/paused
- Publisher units: the exact existing bob-moltbook-publisher.service and
  bob-moltbook-publisher.timer examined by the sanitized R3.8 effective-unit
  auditor

The check requires owner-owned, non-symlinked, private 0700 config/data/pause
directories, an owner-owned regular single-link 0600 queue under 256 MiB,
and a trusted pause marker. The home itself may have conventional Unix
permissions but must be an owner-owned real directory. The report checks the
legacy SQLite table shape and that R3 tables are absent. Unknown or partial
R3 tables block the rehearsal. Unsafe permissions are reported, NEVER
automatically fixed.

The independent R3 owner settings are categorized as absent/off,
explicitly off, or present/requiring owner review. Their raw values,
timestamps and source path are not printed. Even a legacy v0.7 Auto setting
does not authorize new R3 posts. This check does NOT attest the installed
publisher executable hash, live friend/source files, external GET, Windows
startup, or complete service ownership.

## Safe operator commands

After merging into next, use the normal OpenClawLab WSL account, no sudo:

\`\`\`bash
cd ~/bob-next && git pull --ff-only && python3 scripts/report_r313a_host.py
\`\`\`

This is strictly a read-only source/host metadata review. Only after the
report says "private copy eligible: yes" should the owner run:

\`\`\`bash
cd ~/bob-next && python3 scripts/report_r313a_host.py --private-copy
\`\`\`

Either accepts --json for metadata-only output. Do not run bobctl update,
enable R3 units, alter owner settings or touch the installed schema.

## What --private-copy does

1. Rechecks exact host roots, file ownership, permissions and legacy DB
   contract with a read-only SQLite connection.
2. Creates a 0700 temporary directory and 0600 disposable database.
   SQLite's online backup API copies a consistent snapshot of the existing
   queue, including committed WAL entries; it never raw-copies an active DB.
3. Performs SQLite quick-check, then hashes EVERY legacy row in all five
   legacy tables, including private drafts, decisions, attempts, uncertainty,
   events and replies. Only Boolean preservation status and aggregate counts
   are reported, never private rows or hashes.
4. Deliberately simulates a pre-commit crash after additive DDL and verifies
   full rollback in the temporary copy.
5. Adds R3.5-compatible proposal, owner-approval, audit and version tables
   ONLY to the copy. Rechecks full legacy history, attempted/uncertain counts
   and idempotence on a second migration.
6. Disposes of the private copy on success or failure; refuses every possible
   publishing/cutover authorization.

SQLite read-only WAL access can depend on existing shared-memory files,
but the script performs no live schema, setting or application data changes.
It never loads credential files, sends HTTP, changes units or installs code.
A historical send attempt is NOT a verified public Moltbook comment.

## Offline tests

\`\`\`bash
python3 -m unittest discover -s tests -p 'test_r313a_host_private_copy.py' -v
\`\`\`

The suite covers fixed roots, owner permissions, symlinks, pause state,
explicit Off/independent owner settings, an actively committed WAL entry,
private-copy cleanup, crash rollback, migration idempotence, full historical
row preservation and comparison against the earlier R3.5 schema.

## Still blocking any real R3 activity

- A production additive migration and owner settings UI are not installed.
- Installed publisher path/hash and service process identity are not attested.
- A reviewed real publisher R3 POST branch, fixed-host GET and final
  after-intent source/friend/pause check are still absent.
- Unit drain, owner-approved canary, WSL reboot recovery and rollback need
  their own separate release/authorization gate.
- R2 G1 naturally timer-driven Scout-linked model decision is still pending.

Never restore an old SQLite backup over newer attempted/uncertain publication
history. R3.13a is a private rehearsal, not deployment approval.
