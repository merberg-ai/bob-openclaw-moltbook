# R3.13b: private upgrade/consent contract and installed publisher attestation

**Status: source-only and noninstallable.** No installed schema, owner permission UI,
publisher code, unit, release or Moltbook request changes. R3.12 real dispatch
remains hard Off; the installed legacy v0.7 publisher is still sole real sender.

## OMEN operator acceptance (2026-10-30)

The operator ran both R3.13b commands in `~/bob-next` on the OMEN/OpenClawLab WSL account.

**Read-only source/host result: PASS.** Queue trusted, legacy schema matched, installed R3 controls absent/Off, effective publisher unit reviewed, installed publisher owner-controlled regular, private updater registry hash verified, and zero boundary/source blockers. `different_legacy_release_expected` is the correct informative comparison to the unreleased `next` candidate, not a hash failure or deployment instruction.

**Explicit private-copy upgrade result: PASS.** Crash rollback, second-run idempotence and original history preservation all passed; there were 22 historical send attempts and zero uncertain outcomes in the copied production snapshot. A newly simulated uncertain attempt remained after the code-only rollback review; the temporary copy was deleted. The operator's output states live database and installed publisher unchanged, no new Bob R3 manual/automatic posting rights and no cutover authority.

This is a point-in-time **operator-supplied** acceptance of the source-only rehearsal. It does not certify ongoing process health, a live R3 migration, real post confirmation, or any grant of Bob-authored publishing capability. Do not run `bobctl update` to activate these uninstalled source changes.

## Migration and independent owner controls

The R3.13b upgrade contract only permits changes to a marked, owner-private
disposable SQLite copy named r313b-upgrade-fixtures/r313b-upgrade-copy.sqlite3
with a matching private marker, no other attached database and no symlinks.
It performs a BEGIN IMMEDIATE transaction that adds the reviewed R3.5 proposal,
approval, audit and version tables plus four explicit default-Off keys:

- r3_comment_dial = off
- r3_manual_enabled = 0
- r3_auto_enabled = 0
- r3_auto_since = empty

The existing v0.7 auto_enabled flag NEVER grants R3 permission. Preexisting
non-Off R3 values or unknown schema fail closed without being overwritten.
Migration verifies every previously existing legacy record, not merely send
totals. Pre-commit crash rollback, idempotence and existing Off preservation
are tested.

A future separate owner UI must require authenticated admin intent before
changing those keys. A Bob-authored manual draft requires a separate R3 manual
enable, compatible dial and exact owner-approved draft seal. Auto requires
separate R3 auto consent, valid opt-in timestamp before the source run, and
existing legacy auto consent. The read-only capability evaluator NEVER grants
dispatch, even if it observes synthetic permissions. **No actual owner UI or
production setting writer is installed by R3.13b.**

A code rollback must NEVER restore an outdated full SQLite snapshot over
newer attempts, uncertain sends, approvals or replies. Code-only rollback
leaves the CURRENT database in place. The rehearsal inserts a synthetic new
uncertain attempted send into the disposable copy after upgrade and verifies
it remains present through the rollback review.

## Actual installed publisher source evidence

The metadata-only reader obtains the effective exact existing
bob-moltbook-publisher.service/.timer via the existing R3.8 systemd parser.
It rejects extra commands and ambiguous ExecStart paths, confirms a single
absolute non-symlink owner/root-controlled executable, rejects writable
ancestors and changing file metadata, and hashes executable bytes internally.

If the publisher is tracked by the private updater registry, that local
recorded hash must match. If it is untracked, the report says so rather than
inventing assurance. The comparison with the future next-branch source
candidate is informational: the installed v0.7 publisher is expected to be
different from the not-yet-installed R3.12 code. No paths, environment values,
raw hashes, passwords or command bodies appear in the report. A matching
local registry is not cryptographic release signing or new R3 permission.

## Operator instructions after merge into next

1. Run the fixed read-only check in OpenClawLab as the normal account:

       cd ~/bob-next && git pull --ff-only && python3 scripts/report_r313b_host.py

2. Only if the host boundary is eligible, run the disposable real-queue
   SQLite snapshot and migration rehearsal:

       python3 scripts/report_r313b_host.py --private-copy

Both commands accept --json for sanitized metadata. The second snapshots
committed WAL with SQLite online backup into a 0600 temp database under a
0700 owner-private directory; it migrates the COPY only, verifies pre-commit
crash recovery, idempotence, Off controls, complete history and preservation
of a new post-upgrade synthetic uncertain attempt, and then deletes the copy.

No credential reads, POST requests, live database DDL, systemd control, owner
permission or updater installation are performed. Do NOT run bobctl update
for R3.13b, or change the live R3 permissions.

## Tests, limitations and next stages

Offline focused test command:

    python3 -m unittest discover -s tests -p 'test_r313b_upgrade_attestation.py' -v

Full CI also exercises prior R3 tests. The source-only contract is NOT an
executable production migration, an owner control page, or an R3 POST branch.

R3.13c must review the actual single installed publisher production admission
and send path, authenticated exact post/author GET, fresh friend/owner/source
evidence, durable intent and final after-intent check with challenge/unknown
recovery; independent authenticated owner permission controls must be wired
through a versioned install. R3.13d must separately get explicit owner approval
for staged cutover, service drain, canary, WSL/Windows reboot and code-only
rollback. R2 G1 remains independently pending.
