# R4 private proposal-only activation: signed compatibility patch

## Status and boundary

R4 `v0.8.0-autonomy1` is installed and accepted on the OMEN. The owner
confirmed the private-LAN Activity Manager and `/r4/` work correctly. All
R4 public social sends and automatic social worker modes remain compiled Off.

**Release candidate `v0.8.0-r4propose1` is NOT current, NOT installed
and NOT authorized yet.** It fixes a real mismatch between the R4 producer's
session key and `bob_v08.shadow.openclaw_decide`'s trusted prefix. Synthetic
model callback tests previously bypassed the strict transport check.

The four-file patch:
- changes R4's private session ID to the distinct, accepted
  `moltbook-v08-shadow-r4-proposal-<saved Scout source run>`;
- preserves OpenClaw `--agent main` and the private prompt file;
- adds the new exact HTTPS release identity to updater and `bobctl`;
- extends R4 signed installed attestation to **both** exact known R4
  releases, including source hashes for the existing proposal worker;
- requires accepted installed `autonomy1`, completed verified registry,
  existing unique publisher topology, restored R4 schema, private HTTPS and
  **zero attempted R4 public actions** before owner-typed patch installation;
- preserves the one-step signed code/registry-only rollback to the immediate
  predecessor; never restores old SQLite.

No publisher, agent personality, OpenClaw package, model, legacy service,
Scout schedule, R4 database schema or manager route is changed by source
checkout. The patch restarts only the existing HTTPS manager during a
separately signed owner-typed updater transaction.

## After release review, exact manifest promotion and owner installation

Do **not** run an installed `bobctl update` until the new HTTPS release is
recognized by that installed updater. The trusted updated checkout's
`scripts/bob_release_updater.py` is the reviewed bridge.

First, from the clean trusted `~/bob-next` checkout, run the separately
promoted, signed new-release preflight and `--check`. Only after inspecting
the exact four-file offer and typed approval should a human run the updated
source updater, type `UPDATE`, and verify read-only
`scripts/report_r4_installed.py --check`. This is NOT the same as enabling
private proposals.

No systemd timer/service is created for R4 proposals by this patch.
The **first trial is a deliberate single manual decision**.

## First private proposal trial: once, not scheduled

After the installed R4 patch acceptance PASS, use the existing Activity
Manager over the private LAN:

1. In `/r4/controls`, set **Upvote = Propose** using the exact confirmation
   `SET R4 UPVOTE PROPOSE`. This stores only a local owner permission.
   Optionally enable **Comment = Propose** with
   `SET R4 COMMENT PROPOSE`. Leave Post, Follow, Reply, Unfollow Off
   for the first smoke. **Never select Auto**.
2. Separately set `R4 global pause: OFF` with exact `RESUME R4`.
   This affects R4 only. The existing publishing/Scout permissions do not
   change.
3. On the OMEN as non-root `openclaw`, run exactly one already
   **installed and signed** R4 proposal:
   ```bash
   ~/.local/bin/bob-r4-propose --once
   ```
   The expected sanitized JSON `status` is `proposed` (Inbox has one
   source-sealed private decision), `skipped` (Bob genuinely abstained),
   or `none` (paused, no fresh saved eligible Scout source, or all actions
   Off). `refused` is a diagnostic, not a reason to unlock public sending.
   Always require `queued:false`, `attempted:false` and
   `dispatch_authorized:false`.
4. If proposed, inspect `/r4/inbox` and Bob's reason. This proposal has
   **no public effect**. Do not queue or approve an upvote for first smoke.
   A model response that fails the eight-field source/target schema is
   rejected and does not consume the saved Scout source.
5. A source must be less than 48 hours old and not previously consumed
   by R3 proposals or publication jobs. If the result is
   `none/no_fresh_r4_source`, let normal Scout collect a new feed;
   do not reset existing decisions or replay historical R3 sources.

A manual pause can be restored at any time through `PAUSE R4` in Controls.
Auto and all real public sends remain source-inaccessible independently of
these controls. **No scheduled R4 proposal timer is part of this patch.**
The owner can separately review a bounded schedule only after manual
one-shot acceptance.
