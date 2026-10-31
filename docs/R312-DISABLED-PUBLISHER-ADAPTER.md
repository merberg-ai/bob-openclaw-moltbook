# R3.12 Disabled Publisher Adapter and Fake-Credentialed Acceptance

**Status:** source-only development candidate, `R312_REAL_DISPATCH=False`, **NOT installable** and **NOT an owner authorization to publish Bob-authored comments**.

## Integrated with the existing publisher, safely Off

`src/lib/bob/bob_r312_adapter.py` is now imported by the **same**
`src/bin/bob-moltbook-publisher` executable that performs legacy v0.7
publication. No second unit or credentialed worker was added.

The normal publisher step continues to call the same legacy Scout
`load_record()`, manual-decision and friend gates, exact v0.7 policy, intent
CAS, Moltbook HTTP request, challenge and unknown-delivery recovery. The
deliberate change is **selection only**:

- When the additive `r3_proposals` table is absent, the publisher runs the
  original legacy queue selection SQL, with identical manual-first/FIFO order.
- When it is present with the required columns, queued rows bound to an R3
  proposal are **excluded from legacy Scout validation**, rather than
  incorrectly marked as failed Scout drafts. Unrelated Scout jobs remain
  eligible for the existing single credentialed publisher. An invalid
  `r3_proposals` shape fails closed before any publication attempt.
- If the only queued jobs are R3 Bob drafts, the normal step returns
  `R3 Bob-authored queued drafts held; no R3 production dispatcher`. It
  does **not** change their state, record `attempted_at`, fetch Moltbook or
  consume credentials. Independent owner R3 flags cannot override the
  compile-time `R312_REAL_DISPATCH=False` condition.

**The installed OMEN release is not changed by merging source into `next`.**
If an unmodified v0.7 publisher were ever handed an unrecognized R3 job,
it would still use the old Scout-only validator; creating real R3 jobs before
a reviewed installation remains prohibited.

## End-to-end fake-credentialed POST rehearsal

The same publisher executable adds an **explicit**, separately gated
`--r312-fake-credentialed <marked-private-R3-fixture>` subcommand.
It cannot be invoked by the normal timer or manager UI.

The test entrypoint calls `src/bob_v08/r312_fake_credentialed.py`, which
requires the private marker/0600 descriptor and verified Scout evidence
already established in R3.11. It then runs the R3.9 trusted read-only review,
R3.10 transactional claim under `BEGIN IMMEDIATE` in the legacy-shaped
`publish_jobs` ledger, and R3.8 last source/friend/consent/pause/budget
barrier. After a durable synthetic intent, the exact target/text is
delivered to **`FakeCredentialedTransport`**, which enforces an in-memory
fake key and an exact POST-shaped method/path/payload. This transport does
not import sockets, urllib, the Moltbook client or credentials.

- A fake acknowledgement records `acknowledged_simulated`, never
  `published`. A fake challenge remains `awaiting_verification_simulated`
  for human handling. Fake timeout, malformed and unsuccessful results
  lock `attempted_at` in an uncertain state with no auto retry.
- Crashes after intent or after fake delivery preserve the consumed attempt.
  Subsequent invocations cannot send again. Existing v0.7 uncertain
  publication rows are left alone.
- The real publisher CLI prints sanitized metadata: fake POST count,
  attempted-intent boolean, and `external_requests=0`,
  `production_credential_reads=0`, `installed_changes=0`, with
  `dispatch_authorized=false` and `cutover_authorized=false`.

The `tests/test_r312_disabled_adapter.py` suite exercises the real
publisher `publisher_step()` via mocks and the actual executable in a
subprocess with a private `HOME`: R3-only held, old approved Scout
publication using fake API, old schema unchanged, untrusted R3 table
refusal, fake exact-key POST, revoked Off settings, fake timeout/challenge,
late pause, process competition and restart without replay.

## Versioned candidate and safe rollback

`releases/candidates/r312-adapter-off.json` is **noninstallable metadata**,
not a live release or updater file. `releases/current.json` remains
`v0.8.0-shadow4`. No startup commands, systemd units, owner consent, live
database schema, API credentials or actual Moltbook operations were modified.

Rollback **at this stage** is simply omitting or reverting the source commit.
A future installed rollback must never restore old SQLite bytes over newer
attempted or uncertain history. R3.12 CI acceptance does not prove the OMEN
is configured for this version; R3.6/R3.8 operator host snapshots still
refer to the existing legacy setup.

## Remaining before any real R3 posting (R3.13+)

1. Authenticated source-root and owner settings from the installed WSL host,
   including the separate R3 owner permission UI and a safe additive schema
   migration preserving old `publish_jobs`, approvals and attempts.
2. A future reviewed single-publisher R3 production send branch, with a
   real fixed-host HTTPS GET, exact author/post check, and final
   source/friend/consent/pause barrier after an atomic persisted attempt.
   No model or dashboard-supplied `friend_clear` or `GET_ok` can authorize.
3. A versioned operator-approved install, unit drain/reboot test, canary,
   and code-only rollback plan. No blind retries after uncertain delivery.
4. **Separate explicit owner authorization** for any new R3 manual or
   automatic publication capability; v0.7 `auto_enabled=1` is insufficient.
5. A naturally timer-driven source-linked R2 model decision remains an
   independent outstanding acceptance item.

**Do not use `bobctl update` or modify OMEN for this source checkpoint.**
