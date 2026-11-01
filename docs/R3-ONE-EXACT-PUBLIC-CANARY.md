## 2026-11-01 real host acceptance: one public canary PASSED

The owner installed the exact seven-file signed `v0.8.0-r3canary1` from
`v0.8.0-r3skip1`, then confirmed authenticated HTTPS, R3 controls, original
service topology and signed exact-scope installation checks all PASS. In the
original /r3 owner UI they separately approved and queued the exact Bob draft;
the signed `bob-r3-canary-arm --check` returned READY_TO_ARM; interactive
`--arm` with the exact source run returned ARMED. No API request was made by
the arm command itself.

At **Nov 1, 2026, 11:46:08 PST** the *existing* publisher's natural
systemd service logged `R3 candidate outcome: api_acknowledged`, completing
the one allowed attempt. The fixed read-only local receipt report returned
`state=published`, `attempt_recorded=true`, stable queue record, no other
attempted local job at this target and exact saved comment ID
`8c37f88f-e678-4007-ba56-586b76ef4cfd`. The independent bounded public
GET returned `public_observation=visible_in_public_listing` and
`independently_visible=true`. User-shared subsequent publisher ticks showed
no queued work. `retry_authorized=false`,
`external_duplicate_excluded=false` and
`api_ack_is_public_receipt=false` are correctly preserved.

**R3 first genuine public canary is accepted.** This does not enable broad
R3 or R4 automatic publication, nor imply globally proven nonduplication.
The attempted source must remain consumed; do not reset it or rearm. The
one-run pin expires at the original UTC deadline, and the R4 release must
preserve historical attempted/receipt states while defaulting new
permissions Off or Propose.

---

# R3 first genuine, owner-approved, one-comment public canary

Status: **source candidate only** until GitHub CI and separate owner-confirmed
OMEN installation succeed. This is NOT the consolidated R4 release and not
permission for ChatGPT or a script to publish autonomously.

## What is irreversibly pinned in reviewed source

- Bob's natural Scout run: `20261101T151033Z`
- Original target post: `bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a`
- Independently verified exact owner approval seal:
  `870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2`
- Final canary expiry: **2026-11-05 00:00 UTC** (November 4, 4 PM PST).
  That expires before the producer's seven-day manual source-age limit.
  A delayed rollout must **stop**, not extend time without a new review.

The owner used the authenticated HTTPS `/r3` page to approve this one exact
Bob-authored draft but did **NOT** queue it. The previous owner-only read-only
report confirmed the same run, post and 64-character seal with
`owner_approval_verified=true`, `queue_state=none`,
`attempt_recorded=false` and `canary_send_authorized=false`.
No one has authorized a public send merely by installing or approving.

## One installed signed release, two *separate* actions before any POST

`v0.8.0-r3canary1` is an explicit seven-file release from installed
`v0.8.0-r3skip1`: the original updater, bobctl, canary ZIP,
`bob_r3_canary_lock.py`, `bob_r313c_adapter.py`, the SAME credentialed
`bob-moltbook-publisher` and `bob-r3-canary-arm`. There is **no** Activity
Manager replacement, second publisher, Scout replacement, DB schema migration,
new timer, model-side API key, public listener, or auto-switch.
The original `R312_REAL_DISPATCH`, `R313C_REAL_DISPATCH`,
and `R3_AUTO_UI_COMPILED_OFF` remain False, False and True respectively.
The narrow one-canary import boundary is enabled, but **cannot dispatch**
without the explicit owner-arm file. Existing `r3skip1` and `r3format1`
ZIP builders are frozen to their exact historical module bytes.

The old R3skip1 updater does not recognize the future r3canary1 HTTPS release
name. For **this one updater compatibility hop**, use the reviewed `next`
checkout script directly, not the old installed `bobctl update`. It retains
the same exact release/from manifest, typed `UPDATE`, owner preflight,
verified SQLite backup, installed SHA registry, authenticated HTTPS postflight
and automatic code-only rollback. Do not manually replace installed files or
bypass any preflight refusal.

After CI passes and the PR merges to `next`, on OMEN:

```bash
cd ~/bob-next
git status --short
git pull --ff-only
python3 scripts/bob_release_updater.py --check
python3 scripts/bob_release_updater.py
# Only after reviewing the exact candidate, type UPDATE when prompted.
python3 scripts/report_r3_canary_installed.py --check
```

The checkout must be clean, on branch `next`, current installed release
must match `v0.8.0-r3skip1`, and installation acceptance must say
`acceptance: PASS`. It verifies the source pin, byte hashes, original
authenticated CA HTTPS `/r3`, existing timer topology, and all separate
broad-dispatch gates. **A PASS is not publication**.

**Separate owner action 1 (queue only):** In the actual HTTPS `/r3` owner UI
find the *same* exact approved source run above and type
`QUEUE BOB COMMENT` for that one card only. The normal publisher timer
still cannot send R3, because the owner-arm file does not exist.
Do not queue a different draft as a substitute.

**Separate owner action 2 (irreversible publication authorization):**

```bash
bob-r3-canary-arm --check
# Must say READY_TO_ARM, with no send.
bob-r3-canary-arm --arm
# Type the exact displayed: ARM BOB R3 20261101T151033Z
```

`--arm` requires an interactive TTY, matching installed signed file hashes,
normal non-root OpenClaw owner, exact verified and queued head of the
single shared publisher ledger, manual-not-auto R3 owner mode, matching
saved source/seal, no prior attempt to the same target, and unexpired source.
Only then does it exclusively create a fixed private 0600 capability file.
It never calls the Moltbook API itself, and it never starts a second worker.
After `ARMED`, the EXISTING publisher timer may **attempt ONE REAL PUBLIC
COMMENT** on its next natural tick. Do not run it manually to accelerate
the public test.

The existing publisher will still perform anonymous fixed-host post/author
GET, exact original source/envelope/draft checks, pause, queue precedence,
daily/cooldown policy, atomic durable `attempted_at` before sending, late
owner/source/limits checks, final signed-file re-attestation, final immutable
target/expiry verification, then its own original credentialed
`POST /posts/{id}/comments`. A timeout, 401, 405, challenge, crash, or
incomplete ACK **never** automatically resends. The permanent attempt record
prevents a second R3 publication attempt. If expiry passes, stop.

## Reconcile a real attempt, do not fabricate success

```bash
journalctl --user -u bob-moltbook-publisher.service --since "1 hour ago" --no-pager -n 30
cd ~/bob-next
python3 scripts/report_r3_canary_receipt.py --check
python3 scripts/report_r3_canary_receipt.py --public-get
```

The receipt script opens the fixed private queue in SQLite `mode=ro`,
`query_only`. Optional public GET asks only the fixed Moltbook host for
the exact saved comment ID, bounded to two pages and no redirect/credentials.
A remote acknowledgment with a valid comment ID is **not** independently
publicly verified until that GET actually finds it. `public_check_unavailable`,
`scan_incomplete`, `uncertain` or `id_unconfirmed` mean STOP, investigate
without retry. Even a visible receipt is not absolute proof that no
unobserved external duplicate exists. Other legacy writer history remains
untouched. The normal pending drafts stay pending unless explicitly reviewed.

Moltbook community users have reported comment endpoint 401 and GET 405
behavior at times, so do not weaken sender or receipt validation to force
a green milestone. Never assume an API call succeeded after timeout.
This is a single bounded attempt, not a bulk source unlock.

## Acceptance and recovery boundaries

Release CI must demonstrate deterministic ZIPs, frozen prior accepted ZIP
bytes, exact immutable source/target/seal, no-arm default Off, expired,
tampered and broad-auto refusal, one shared credential owner, duplicate-safe
atomic intent, no network during CLI checks, and immutable no-retry outcome
after ambiguous delivery. Re-run installed HTTPS/owner/timer checks before
arming, and inspect the queue head after queueing. A failed updater uses its
original code-only rollback; never restore a database over a potentially
accepted public attempt. An arm marker remains scoped to **this exact**
release/run/seal/expiry; future releases with different pinned identities
will not accept it.

Do not merge the broader R4 draft PR #132 as part of this canary. Once the
owner verifies a *real* public receipt or deliberately stops after an
unconfirmed attempt, record the boundary, then resume R4 as one integrated
feature/release milestone.
