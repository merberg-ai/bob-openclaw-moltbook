# R4 private proposal-only activation: signed compatibility patch

**Installed and accepted on OMEN (owner-confirmed, 2026-11-01 PST):**
`v0.8.0-r4propose1` completed the owner-typed `UPDATE` and independent
`report_r4_installed.py --check` returned `acceptance:PASS`.
All signed registry, authenticated private HTTPS, R4 routes and versioned
schema checks passed. The original publisher was inactive and there were
zero R4 public action attempts; public dispatch stays disabled. Earlier
pre-installation/failed-attempt instructions below are preserved for audit,
not an instruction to repeat installation. **Next step is only the manual
private one-shot trial under the existing authenticated R4 Controls.**


## Status and boundary

R4 `v0.8.0-autonomy1` is installed and accepted on the OMEN. The owner
confirmed the private-LAN Activity Manager and `/r4/` work correctly. All
R4 public social sends and automatic social worker modes remain compiled Off.

**Source release promotion PR #140 offers `v0.8.0-r4propose1`, but it
is NOT installed and does NOT authorize any public action.** It fixes a real mismatch between the R4 producer's
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

## Exact operator installation handoff, only AFTER PR #140 merges

In OpenClawLab as the normal non-root `openclaw` account, using the
reviewed and clean `next` checkout:

```bash
cd ~/bob-next && git pull --ff-only && \
PYTHONDONTWRITEBYTECODE=1 python3 scripts/report_r4_proposal_candidate.py --check && \
python3 scripts/bob_release_updater.py --check
```

Expected: the source report identifies the exact **four-file**
`v0.8.0-r4propose1` release, with `all_r4_public_sends_hard_off:true`.
The updater `--check` only displays the offer. **No installation yet.**

After you have reviewed the output and chosen to install, run separately:

```bash
cd ~/bob-next && python3 scripts/bob_release_updater.py
```

The trusted updater repeats the host acceptance gate and requires that you
type `UPDATE` for exactly `v0.8.0-r4propose1` and the expected four
files. This is a real, one-time signed update and restarts the existing
private HTTPS manager. It does not migrate SQLite or set proposal modes.

Verify the resulting installed state before attempting a model call:

```bash
cd ~/bob-next && python3 scripts/report_r4_installed.py --check
```

Expected: `release:v0.8.0-r4propose1`,
`acceptance:PASS`, `new_r4_actions_attempted:0` and
`public_send_armed_by_report:false`. If a check refuses, do not enable
controls or try to repair the DB/installed files manually.

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

## Interruption / refused patch triage (no automatic retry)

The owner attempted the promoted four-file patch, typed `UPDATE`, and
received only `BOB UPDATE: REFUSED (ValueError)`. Follow-up read-only
inspection confirmed that `v0.8.0-autonomy1` remains hash-verified, the old
journal is `complete`, no `tx-v0.8.0-r4propose1` archive exists, and local
HTTPS/SQLite schema/signature are healthy with zero R4 sends.

Do not run `--recover` or rollback when the original journal remains
complete. Do not repeatedly type `UPDATE` without investigating. The generic
ValueError does **not** identify which early pre-archive gate refused; a
publisher-timer race is a plausible but unproven explanation.

From the trusted checkout, after a simple `git pull --ff-only`, run the
read-only sanitized check:

```bash
cd ~/bob-next && PYTHONDONTWRITEBYTECODE=1 python3 scripts/report_r4_patch_refusal.py --check
```

It reports only allowlisted booleans and identifiers, never credentials,
database contents, raw systemd unit text, network payloads, or private paths.
A green result reflects conditions **now**, not the historical failed instant.
It never retries, installs, creates a database backup, invokes OpenClaw, changes
a service or makes any Moltbook API call.


## Categorical pretransaction refusal diagnostics (source-review stage)

After a second typed `UPDATE` refusal, the owner separately ran a private
SQLite online backup and isolated restore rehearsal. Both passed. The original
`autonomy1` registry/journal remained signed and complete, and no patch
archive existed. This does not establish which earlier gate failed.

A reviewed follow-up adds strictly allowlisted diagnostic stages to the
existing source updater **before** any installed-file changes:
`state_directory`, `updater_lock`, `publisher_topology`,
`prior_journal`, `installed_hashes`, `authenticated_https`,
`verified_sqlite_backup`, `archive_absence`, `archive_creation`,
`archive_original_files`, `archive_checksums`, `archive_registry`
and `transaction_journal`. Only hardcoded stage labels and exception
types are printed, never raw errors, credentials, paths or HTTP content.

This is observability, **not** a bypass. The same exception still aborts
the update; no automatic retry, stop/start command, R4 action-mode change,
new public writer, or social action is introduced. The ordinary signed
transaction rollback remains intact.

## Real Bob model call refused: one separate private diagnostic

The owner-enabled R4 Propose trial selected an actual sealed saved Scout
observation (`20261102T042747Z`), then returned
`r4_model_or_contract_unverified`, with `queued:false`,
`attempted:false` and `dispatch_authorized:false`. That aggregate label
covers both failure of the original OpenClaw main-agent CLI/envelope and
rejection of Bob's strict eight-string-field JSON. The failing source is
not consumed, and **no public Moltbook request occurred through R4**.

Do not disable validation, copy the raw model payload into a chat/log,
change the existing publisher, or keep repeating the uninstrumented worker.

After review and merge of the source-only probe, an operator may voluntarily
run exactly one targeted diagnostic:

```bash
cd ~/bob-next && git pull --ff-only && PYTHONDONTWRITEBYTECODE=1 python3 scripts/report_r4_agent_contract.py --once
```

This is NOT a release installation, and it cannot approve, queue or publish
an R4 action. It verifies the **installed signed** R4 bridge and uses a
distinct `moltbook-v08-shadow-r4-diagnostic-<source_run>` session. It calls
the real local OpenClaw main agent **once** and OpenClaw may save a local
agent session. It only reports transport vs contract errors selected from a
hardcoded allowlist, never model responses, file paths, credentials, Scout
body, or raw stderr. SQLite is opened `mode=ro`, with
`PRAGMA query_only=ON`; no private R4 decision is committed by this probe.

A `valid_private_decision` means this independent model response passes the
original schema and permissions but **does not create a proposal**. Do not
mistake it for a persisted Inbox item. The original `bob-r4-propose --once`
remains the only approved way to record a private decision. A
`source_not_recent` or `source_already_used` refuses without calling
OpenClaw; never replay or alter the original time/used-source checks.

R4 scheduling, Auto, real public votes/comments/posts/follows, and all
new public publisher privileges remain disabled regardless of results.


## Historical Scout source claimed between R4 refusal and contract probe

The owner's first diagnostic for `20261102T042747Z` returned
`source_already_used` before any model call. This does **not** resolve the
earlier `r4_model_or_contract_unverified` error. A refused R4 model response
does not commit a social decision, but the existing scheduled R3 or publisher
may have claimed a Scout source afterward.

The follow-up diagnostic now follows the installed producer's bounded
sealed Scout selection: latest 20 valid observations from up to 100 files,
within 48 hours, excluding R4, R3 and publication ledger-consumed runs.
It can show the previous fixed source's current ledger owner as a sanitized
category, never the post text or database rows. There are no new model
instructions or relaxation of the eight-field contract. If no unused
source exists, it returns `no_fresh_r4_source` without invoking OpenClaw.
The user should let normal Scout gather new source records; do not reset
or replay any previous run.

The operator invocation remains the same single `--once` command after
pulling the reviewed change. A successful diagnostic means the model
completed a valid **unsaved** decision; an OpenClaw call may persist an
isolated agent session even though it never creates a social proposal.
