# R4 schedule1: private proposal timer, OFF-first owner handoff

**Scope:** `v0.8.0-r4schedule1` is a signed, incremental code update
from the owner-accepted `v0.8.0-r4format1`. It does NOT create or enable a
systemd timer, change R4 mode, schedule a model call, or authorize any public
Moltbook request when the updater runs. All host steps below require the
owner's separate, interactive approval.

## What is already accepted

The OMEN previously installed and independently accepted the signed
`v0.8.0-r4format1` release. A genuine OpenClaw R4 one-shot returned a
durable `skipped` decision with reason `bob_abstained` for source
`20261102T105527Z`, and all queued, attempted and dispatch-authorized
flags were false. We do not need to force a public or private proposal.

The new scheduling module targets the **same** signed R4 decision producer
and existing SQLite ledger, with the same exact eight-field JSON contract.
It does not add an R4 publisher or a public Moltbook API client.

## What is installed and what remains inert

The versioned updater proposes six exact signed files only:
`bob-release-updater`, `bobctl`, `bob_r4_installed_gate.py`,
`bob_r4_schedule.py`, `bob-r4-schedule`, `bob_r4_web.py`.

The existing HTTPS Activity Manager restarts to expose read-only status on
`/r4/controls` and `/r4/diagnostics`. The updater **does not** install
`bob-r4-propose.service` or `bob-r4-propose.timer` and never starts either.
Its private SQLite backup/transaction is for code installation only; it
does not migrate the database, change preferences or delete receipts.

The **separate**, owner-gated `bob-r4-schedule` CLI owns those two exact
user-systemd unit files. No shell commands or file paths are supplied by
the model, a dashboard request, or an untrusted Moltbook post.

Cadence: `OnActiveSec=120min`, `OnUnitInactiveSec=120min`,
`RandomizedDelaySec=10min`, `AccuracySec=1min`, and
`Persistent=false`. No catch-up on reboot, no `Restart=always`, no
forced activity on activation and no automatic model retry.

Before **each** scheduled run, the worker checks the exact signed
release/registry, current schedule journal, original publisher and R3
one-shot service inactivity, active Scout/R3/publisher timers, existing R4
modes and global pause, and unit bytes without drop-ins. The signed R4
producer rechecks source freshness and all three consumed-source ledgers,
then applies the unchanged strict model/ledger rules. The timer cannot
create a `publish_jobs` record or dispatch, vote, comment, follow, or post
as a public R4 action.

## Source-only acceptance, NO host changes

Once PR CI is green and merged into `next`, as the normal `openclaw` WSL
user from the trusted `~/bob-next` checkout:

```bash
cd ~/bob-next &&
git pull --ff-only &&
python3 scripts/report_r4_schedule_candidate.py --check &&
python3 scripts/bob_release_updater.py --check
```

Expected: exact candidate `v0.8.0-r4schedule1` from
`v0.8.0-r4format1`, **six** signed files, hard-Off for public R4
dispatch, no DB migration, no automatic timer creation/enable. The second
command explicitly says `CHECK ONLY`. A failure is a stop condition;
do not bypass a gate or edit the installed registry.

## Physical test A: separately signed code install

Only after the source-only checks pass, the owner may choose:

```bash
cd ~/bob-next && python3 scripts/bob_release_updater.py
```

Review the exact offer, then type `UPDATE` once. The signed updater
verifies original publisher topology, signed prior installation and HTTPS,
takes a verified private SQLite backup, updates only the declared code
files, restarts the existing Activity Manager, and rolls back code if
HTTPS postflight fails. It never restores a stale database over activity
history.

After `BOB UPDATE: updated`:

```bash
cd ~/bob-next &&
python3 scripts/report_r4_installed.py --check &&
~/.local/bin/bob-r4-schedule --check
```

Require installed `release:v0.8.0-r4schedule1`,
`acceptance:PASS`, authenticated HTTPS, signed original publisher, R4
action attempts 0. The schedule check must say `phase:absent`,
`timer_enabled:false`, `ready_to_stage:true` before unit staging. An
unexpected timer or unit collision is a refusal, not an invitation to
overwrite it. The `--check` command does NOT create a state directory,
systemd unit or model call.

## Physical test B: install units but KEEP TIMER DISABLED

As the same user, separately run:

```bash
~/.local/bin/bob-r4-schedule --stage
```

Type exactly `STAGE R4 SCHEDULE` at the terminal prompt. The stage
creates two exact user-unit files (private regular files), a private
durable journal and requests user-systemd daemon-reload. It verifies
both units are loaded but inactive and that the timer is **disabled**.
No OpenClaw call, publisher change, and no systemd enable occurs here.

Verify:

```bash
~/.local/bin/bob-r4-schedule --status
systemctl --user list-timers --all bob-r4-propose.timer
```

Expected: `phase:staged`, `timer_enabled:false`,
`ready_to_enable:true`. The authenticated Activity Manager
`/r4/controls` and `/r4/diagnostics` show the same read-only state.
If mode Propose or R4 global RESUME was revoked, activation must refuse.

## Physical test C: owner explicitly enables proposal scheduling

This is intentionally a **separate choice** from code installation and
unit staging:

```bash
~/.local/bin/bob-r4-schedule --enable
```

Type `ENABLE R4 SCHEDULE` exactly. This enables ONLY
`bob-r4-propose.timer`, using a 120-minute interval plus up to 10-minute
jitter, without starting the R4 service immediately.

Observe:

```bash
~/.local/bin/bob-r4-schedule --status
systemctl --user list-timers --all bob-r4-propose.timer
journalctl --user -u bob-r4-propose.service --since "3 hours ago" --no-pager -n 40
```

Expected: `phase:enabled`, `timer_enabled:true`. After a legitimate
scheduled tick, `status:skipped` with `bob_abstained` is a valid
success, `status:proposed` is only a private reviewable intent, and
`status:none` may indicate no fresh source, a paused R4, or another
worker temporarily busy. Any `refused` needs investigation. The
`queued`, `attempted` and `dispatch_authorized` values must remain
false. No manual repeated worker retries.

A monitored, owner-triggered service run after schedule enable may
optionally be tested with `systemctl --user start bob-r4-propose.service`.
It uses the same guard as a timer tick and does not grant any new public
authority. Do not start it repeatedly just to provoke engagement.

## Physical test D: disable timer and reversible unit cleanup

To stop future scheduled starts without stopping a worker currently
executing:

```bash
~/.local/bin/bob-r4-schedule --disable
```

Type `DISABLE R4 SCHEDULE`. Verify
`phase:disabled` and `timer_enabled:false`.
If an already running one-shot is still in flight, the command reports
that rather than claiming to have terminated it.

Once no R4 worker is active, to remove only the exact owned units:

```bash
~/.local/bin/bob-r4-schedule --recover
```

Type `RECOVER R4 SCHEDULE`. This disables the R4 timer (if still
loaded), removes only matching private unit files, daemon-reloads
user-systemd and leaves a private `rolled_back` journal. It **never**
rolls back or clears private R4 decisions or Moltbook receipts.

The completed-release updater's owner-typed code-only rollback to
`v0.8.0-r4format1` is intentionally **refused** while R4 schedule unit
files exist. Recover units first, then use the separate approved
`python3 scripts/bob_release_updater.py --rollback-r4` procedure only
when actually needed. No SQLite restore.

## Refusal and recovery

An unknown systemd fragment, drop-in, symlink, service already active,
unexpected timer, untrusted owner, unreadable journal, changed unit
bytes, non-verified signed release, busy R3/publisher, paused or
non-Propose R4 controls all fail closed.

After an interrupted operation, inspect `--status` and private
`~/.local/state/bob-r4-schedule/journal.json` before choosing an
owner-typed `--recover`. Unknown or tampered files are **not**
overwritten or removed. Never edit SQLite source ledgers to unblock
a scheduling attempt. The normal Scout and the original publisher
timers remain untouched throughout.

## Offline work completed before physical testing

The repository includes simulated systemd and owner state fixtures for
stage/enable/disable/recovery, collision and symlink refusal, schedule
pause/mode blocking, drift and malformed worker outputs, failure rollback,
crash after journal+files and no model call without signed provenance.
A second isolated transaction rehearsal applies the **actual six candidate
file payloads**, checks old registry/SQLite data, exercises successful
code-only rollback and failed HTTPS postflight rollback, and rejects
rollback while schedule units exist. None of these tests reaches the
owner's OMEN, OpenClaw agent, real systemd or Moltbook.
