# v0.8.0-r3skip1: proposal-only skip repair

Status: code release candidate; do **not** treat a green CI run as an OMEN
installation or a public canary. This release is intentionally isolated from
the unfinished R4/canary PR #132.

## Evidence / scope

The authenticated HTTPS `/r3` dashboard on November 1 shows multiple actual
source-verified sealed Bob comment proposals. They have
`review none; proposal proposed; queue none; attempt recorded False`.
Thus the **first genuine proposal exists**. No approval or publication is
implied. A separate 10:48 PST natural timer invocation still produced a valid
skip. The original R3 producer did not persist valid skips, so it could select
the same saved Scout run again on the following scheduled tick.

The new `r313d_producer` writes one fixed `r313d_skip` row to the existing
private `r3_lab_audit` after revalidating the exact saved Scout observation.
It uses an immediate SQLite transaction, fails closed on schema/state
conflict, and excludes committed skipped source runs from subsequent natural
selection. Refused model responses, transient errors, malformed responses and
stale files are **not** treated as genuine skips. Existing proposed, owner
reviewed or legacy queued rows are not migrated or overwritten.

## Exact release boundary

`v0.8.0-r3skip1`, signed by the established manifest/channel mechanism:

- FROM `v0.8.0-r3format1`, keeping a distinct historical manifest.
- Only `bob-release-updater`, `bobctl`, and `bob_r3_package.pyz` are
  installed. The ZIP is built by `scripts/build_r3_skip_package.py` and differs
  from the accepted format1 ZIP in **only** `r313d_producer.py`.
- No manager restart, Scout change, publisher change, systemd unit edit,
  database schema change, credential access, HTTP POST or owner approval.
- Existing R3 dispatch flags `R313C_REAL_DISPATCH=False`,
  `R312_REAL_DISPATCH=False`, `R313C_INTEGRATION_COMPILED_OFF=True`,
  and `R3_AUTO_UI_COMPILED_OFF=True` are checked by the host preflight.
- Current private HTTPS CA authentication, original legacy publisher, Scout,
  proposal timer and existing pending sealed proposals are preserved.
- An explicit typed `UPDATE` remains mandatory; original code is backed up
  and recoverable. SQLite is backed up before installation but never rolled
  back over a possible public action.

## Installation via the reviewed updater in the next checkout

**Only after CI is green and the release PR is merged to `next`.**
Do not install from an unreviewed feature checkout or while the publisher
or proposal service is actively executing. The update's preflight verifies
the normal installed host/timer boundaries.

The *old installed* `r3format1` updater knows HTTPS transport only through
`r3format1`. Therefore calling the installed `bobctl update` for this new
release would cause its *post-install* health gate to reject the new ID and
roll back. For this **one compatibility bridge**, run the reviewed, pulled
`next` checkout script directly. It uses the **same** signed-branch checkout,
read-only preflight, typed owner consent, backup, installed registry, HTTPS
health and rollback workflow.

```bash
cd ~/bob-next
git status --short
git pull --ff-only
python3 scripts/bob_release_updater.py --check
python3 scripts/bob_release_updater.py
# Type UPDATE when prompted, only after reviewing the exact release summary.
python3 scripts/report_r3_skip_installed.py --check
```

The `git status --short` output must be empty; if not, stop rather than
overwriting host changes. The candidate's `from` identity must match the
installed `v0.8.0-r3format1`. If the updater refuses or rolls back, do not
manually replace files, bypass the gate or rerun blindly. Diagnose using
the sanitized journal and `bobctl update --recover` only if explicitly
indicated.

After successful installation, the installed `bobctl` and updater recognize
`r3skip1` and the normal `bobctl update` flow resumes for future *pre-registered*
release identities.

## Observe naturally (no source replay)

```bash
journalctl --user -u bob-r3-propose.service --since "1 hour ago" --no-pager -n 30
systemctl --user list-timers --all bob-r3-propose.timer bob-moltbook-scout.timer
```

The first post-upgrade tick may skip a source previously skipped by older
versions, because historical skips were only logged to systemd and cannot
be reliably backfilled into the private DB. That first new **valid** skip
is durable; a subsequent tick should not choose that same source_run again.
It may select another eligible Scout source or say `none`. Never require Bob
to comment or interpret `none` as a failure.

Inspect the current pending sealed proposals using the existing HTTPS
`/r3` controls. No proposal is automatically approved, queued, attempted or
published by this release. The separate R3 **one exact manual public canary**
still needs its own source-level allowlist, approval, signed authorization,
and independent external receipt before the consolidated R4 release.
