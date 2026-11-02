# R3.11: Inert single-publisher entrypoint candidate

**Status: noninstallable source candidate, no production R3 dispatch permission.**

This milestone is the first test that calls the **actual existing**
`src/bin/bob-moltbook-publisher` executable through a new *explicit inert*
subcommand, without replacing its longstanding Scout publication function.
The normal `publisher_step()`, `verification_step()` and `main()` paths
remain unchanged. Comparison to the `next` baseline found the full legacy
`publisher_step()` source **byte-for-byte identical**.

## What is built

- `src/bob_v08/r311_inert_entry.py` accepts only the private,
  marker-verified R3.3 SQLite fixture named
  `r3-unified-fixtures/r3-unified-lab.sqlite3`. The fixed sibling Scout
  directory and a private `r311-inert-action.json` descriptor supply an
  *independently verifiable* Bob comment. Public descriptor permissions,
  symlinks, altered text or unknown DB markers refuse.
- `--r311-inert-rehearsal <private-lab-path>` is recognized by the same
  existing publisher executable. It calls R3.10's strict two-pass
  source/consent check and `BEGIN IMMEDIATE` durable atomic claim, then
  R3.8's in-memory `InertSink` with a fake acknowledgment. It never calls
  the real `api()`, `api_key()`, posting token or an external host.
- `--r311-inert-recover <private-lab-path>` drives the synthetic no-retry
  recovery logic **without replay**. Crashes after intent or after the fake
  send leave the existing `attempted_at` locked and convert in-flight
  synthetic send state to irreversible uncertainty.
- Output is metadata-only: attempted recorded, fake sink call count,
  external request/credential/installed change counts and explicit
  `dispatch_authorized:false`, `acted:false`, `cutover_authorized:false`.
  Raw drafts, passwords, user paths and record contents never appear.
- `tests/test_r311_inert_entrypoint.py` executes the *actual publisher
  executable in a subprocess* under an isolated HOME/PYTHONPATH fixture,
  then verifies the DB/audit output. It covers a successful fake receipt,
  repeated invocation, Off/missing owner R3 settings while legacy auto is
  still enabled, consent revocation, changed comment text, unsafe file
  permissions, forced crashes on both sides of the fake sink, recovery,
  human verification challenge, fake timeout and competing processes.

## Version and isolation

`releases/candidates/r311-inert-only.json` records candidate metadata only.
**It is not an updater manifest and is not installable or automatically
promoted.** `releases/current.json` remains the installed Shadow4 release.
No systemd service or timer, credential file, actual legacy SQLite queue,
manager UI or Bob agent configuration is altered by this change.

The normal credentialed publisher on the OMEN **still knows only the v0.7
Scout draft contract**. The new CLI's successful fake send is not a real
Moltbook POST and cannot grant permission to make one. R3 auto permission
is Off/missing in production; the fixture's permissive settings exist solely
to test positive cases.

## Remaining cutover gates

1. Review a **disabled-by-default production adapter** for R3 new drafts
   inside the *single* credentialed v0.7 publisher. It must preserve existing
   Scout admission and one queue/budget, while ensuring owner settings and
   independent exact Bob-draft approvals are authenticated.
2. Wire a trusted publisher-owned fixed-host HTTPS preflight into that
   live adapter. Immediately before a real POST, repeat the pause/source/
   friend/consent gate, preserve attempted-send history on failure, and
   **never** retry a possibly accepted request automatically.
3. Verify actual WSL/Windows reboot/drain and code-only rollback with an
   operator-accepted versioned release. Do not restore old SQLite files over
   newer attempted/uncertain publication records.
4. Obtain explicit owner authorization for **every new R3 posting ability**.
   The owner's approval to develop R3.11 is not consent to change live posting.
   R2's naturally scheduled source-linked model decision remains a separate
   outstanding acceptance check.

**No OMEN test or update is required for R3.11; the workflow runs in CI.**
