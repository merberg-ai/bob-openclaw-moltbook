# Bob: current status

**This is the single source of truth for what is installed and running on the OMEN.** Update it in the same PR as any operator-confirmed host change. Older handoffs, README text and the archived TODO log are history; where they disagree, this file plus fresh host evidence wins (see [precedence](#source-of-truth-precedence)).

_Last updated: 2026-11-02 09:23 PST, from the `bob_evidence.py` bundle the owner ran on OMEN-DESKTOP._

## Installed

| Item | Value |
|---|---|
| Installed release | **`v0.8.0-r4schedule2`** (`from v0.8.0-r4schedule1`); updater transaction `complete` |
| Installed file integrity | 67/67 files match the updater registry; 0 mismatched, 0 missing |
| Source checkout | `~/bob-next` on `next` (docs-only commits behind are fine; pulling never deploys) |
| Activity Manager | `https://192.168.1.24:18790`, private-CA TLS, `/healthz` 200 over loopback HTTPS |
| OpenClaw Gateway | loopback `127.0.0.1:18789`, listening, not LAN-exposed |
| Ollama | `127.0.0.1:11434` listening (model per installed Gateway config) |

## Timers and services (user systemd, `openclaw`)

| Unit | State | Cadence / notes |
|---|---|---|
| `bob-moltbook-scout.timer` | active, enabled | about hourly |
| `bob-moltbook-publisher.timer` | active, enabled | about every minute. **The only credentialed Moltbook writer.** |
| `bob-r3-propose.timer` | active, enabled | 35 min after the previous run finishes. Has the reviewed `10-first-run.conf` drop-in (byte-pinned; never edit). |
| `bob-r4-propose.timer` | **active, enabled** | 120 min + 0–10 min jitter, no catch-up. Private proposals only. |
| `bob-original-worker.timer`, `bob-startup-reconcile.timer` | active | about every 2 min |
| `bob-v08-shadow.timer` | inactive, disabled | R2, retired. Do not re-enable. |
| `bob-activity-manager.service`, `openclaw-gateway.service` | running | |

## Accepted checkpoints (latest first)

- **2026-11-02 09:02:23: first natural R4 timer tick: PASS.**
  - The timer fired and `bob-r4-propose.service` finished with exit 0 in 7 s.
  - The model was called on source `20261102T144124Z` and returned a validated `skipped / bob_abstained`.
  - `queued`, `attempted` and `dispatch_authorized` were all false.
  - The next deadline was 11:06:59.
  - Afterwards `bob-r4-schedule --status` showed `phase:enabled`, `blockers:[]`, `public_dispatch_authorized:false`.
  - It fired earlier than the 09:21:17 `NEXT` shown at enable time. Most likely `OnUnitInactiveSec` was anchored to when systemd first loaded the staged service, and systemd fires on the earliest trigger. Harmless. Dashboards must show systemd's reported times, never computed ones.
- **2026-11-02: R4 timer enabled.** Owner typed `ENABLE R4 SCHEDULE`, got `BOB R4 SCHEDULE: enabled_private_proposals`.
- **2026-11-02: R4 units staged.** `STAGE R4 SCHEDULE` gave `staged_disabled`. The post-stage blocker was `bob-r3-propose.service ActiveState=failed` from an R3 `decision_invalid_model_json` at 06:41:32. After reading the journal, the owner ran `reset-failed` once. That cleared the unit state, not the model-format cause.
- **2026-11-02: `v0.8.0-r4schedule2` signed install, acceptance PASS** (`report_r4_installed.py --check`).
- Earlier R4 (`autonomy1`, `r4propose1`, `r4format1`, `r4schedule1`), R3 (cutover, one public canary 2026-11-01), R2, R1 and v0.7: see [archived TODO log](archive/TODO-log-v0.8.md) and [roadmap](ROADMAP-v0.8.md).

## Hard OFF (not authorized by anything above)

- R4 public dispatch of any kind (comment, reply, post, upvote, follow, unfollow) and R4 `Auto`.
- Any second publisher or credential holder.
- CH1 Chat (the route is reserved and inert).

The one R3 public canary on 2026-11-01 grants no ongoing permission.

## Open watch items

1. **R3 `decision_invalid_model_json`** (seen once, 2026-11-02 06:41). If it recurs, port R4 `format1`'s fresh-session, JSON-only prompting to R3 rather than resetting failures or weakening the parser.
2. **R4/publisher start collision.** At 09:02:23 R4, Scout and the publisher all started in the same second. The publisher runs about once a minute, and R4 refuses while it is active, so some ticks may return `none / r4_schedule_guard_refused`. That is safe. If it is frequent, add a short bounded re-check before refusing.
3. **Queue backlog to explain.** `publish_jobs` has 14 `queued` and `r3_proposals` has 8 `queued`. Confirm whether these are waiting on purpose (manual approval or budget) or stuck.

## In progress (source only, nothing installed)

The [cleanup / dev-loop / Console v2 plan](DEV-LOOP.md) is in progress:
- Phase 0: evidence bundle, `dev.py`, CI.
- Phase 1: this docs consolidation, script archive, single release-ID source.
- Phase 2: Console v2 dashboard with WebSockets and a `/classic` fallback, shipped later as one signed release.

## Source-of-truth precedence

1. Fresh read-only host evidence (`scripts/bob_evidence.py`, installed registry, systemd, verified external receipts).
2. Exact signed installed code and the private DB.
3. This file.
4. `next` source and `releases/current.json`. These describe what could be installed, not what is installed.
5. Archived handoffs, the TODO log and the old README, which are history only.
