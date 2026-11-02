# Bob operations runbook

Run everything as `openclaw` inside OpenClawLab, never as root. Check [STATUS.md](STATUS.md) for what is currently installed. The pre-2026-11-02 operations log is [archived](archive/OPERATIONS-log.md).

## First step for anything: the evidence bundle

```bash
python3 ~/bob-next/scripts/bob_evidence.py                        # last 24 h
python3 ~/bob-next/scripts/bob_evidence.py --since "2026-11-02 09:00"
```

It is read-only and sanitized. Paste it or attach `~/.local/state/bob-evidence/latest.md`. It replaces most of the individual commands below; see [DEV-LOOP.md](DEV-LOOP.md).

## Commands by risk

| Read-only, run any time | Changes state, typed owner approval only |
|---|---|
| `bob-r4-schedule --status` / `--check` | `bob-r4-schedule --stage` (`STAGE R4 SCHEDULE`), already done |
| `systemctl --user list-timers --all` | `bob-r4-schedule --enable` (`ENABLE R4 SCHEDULE`), already done |
| `journalctl --user -u <unit> --since …` | `bob-r4-schedule --disable` (`DISABLE R4 SCHEDULE`) |
| `bobctl status`, `bobctl doctor`, `bobctl publisher-status` | `bob-r4-schedule --recover` (`RECOVER R4 SCHEDULE`), recovery only |
| `python3 scripts/report_r4_installed.py --check` | `python3 scripts/bob_release_updater.py` (`UPDATE`) |
| `python3 scripts/bob_release_updater.py --check` | `bobctl publisher-run`: **may publish a real comment** |

Do not script `systemctl --user reset-failed` or `start` for Bob units. Read the journal reason first, and fix causes in reviewed code.

## Updating to a new signed release

1. The PR is merged to `next` with green CI, and `releases/current.json` names the new release with the exact `from` you have installed.
2. `cd ~/bob-next && git pull --ff-only`. This only updates the source checkout; it deploys nothing.
3. `python3 scripts/bob_release_updater.py --check`. It must offer exactly the expected release and file list.
4. `python3 scripts/bob_release_updater.py`, then type `UPDATE`.
5. `python3 scripts/report_r4_installed.py --check` plus the evidence bundle. Then do the release's short browser checklist.

Do not run `UPDATE` while you are in the middle of checking a timer. Schedule2's code-only rollback refuses while R4 units are staged or enabled.

## Reading R4 outcomes

| Worker output | Meaning | Action |
|---|---|---|
| `none / no_fresh_r4_source` | No unconsumed sealed Scout source | Normal. Wait for Scout. Never replay or reset sources. |
| `none / r4_schedule_guard_refused` | Pre-run topology, mode or signature guard refused, e.g. the publisher or R3 was active at that instant, or the R3 service is `failed` | Read `--status`. Transient collisions clear on the next tick. |
| `skipped / bob_abstained` | Valid private abstention, recorded | Healthy. Do not force a proposal. |
| `proposed` | One private proposal in `/r4/inbox` | Review it. Approving does not queue or publish. |
| `refused / …` | Contract or transport failure, failed closed | Capture the reason code. If it recurs, fix it in reviewed code. |

The `queued`, `attempted` and `dispatch_authorized` fields must always be `false` for R4.

## Incident playbooks

- **Timer shows NEXT but never runs.** Check `list-timers` and `systemctl --user show bob-r4-propose.timer -p LastTriggerUSec`, plus the journal. Do not re-enable it, edit units or force-start the service.
- **`scout_r3_or_publisher_topology_not_idle`.** Usually means `bob-r3-propose.service` is `failed`, or a one-shot was active at the moment of the check. Inspect `journalctl --user -u bob-r3-propose.service`. Only after reading the reason, a single `reset-failed` is acceptable. Never disable the R3, Scout or publisher timers.
- **R3 `decision_invalid_model_json`.** Note the time and source ID. If it recurs, apply a reviewed prompt/session fix modelled on R4 `format1`. Never relax the parser.
- **Dashboard unreachable.** Check, in order:
  1. LAN client CA trust
  2. the certificate
  3. `bob-activity-manager.service`
  4. WSL mirrored networking
  5. the Windows firewall scope for TCP 18790 on `192.168.1.0/24`

  Never disable TLS or expose 18789.
- **Login reset.** See [DASHBOARD-LOGIN-RESET.md](DASHBOARD-LOGIN-RESET.md).

## Never

- Commit or paste secrets, the private DB (or its `-wal`/`-shm` files), CA keys, Gateway tokens, `SOUL.md` contents or raw feed or model text.
- Reset or edit SQLite to get a new outcome.
- Restore a DB backup over newer records without a separate review.
- Run a second publisher.
- Turn on R4 public actions or `Auto`.
- Change Gateway binding or firewall exposure to work around a UI issue.
