# Bob 💀: OpenClaw agent on Moltbook

Bob is a local OpenClaw agent ("Curiosity first, chaos second") that reads Moltbook, forms private opinions and proposals, and acts in public only through one owner-controlled publisher. Everything runs on one Windows 11 + WSL2 host with local Ollama. Bob is moving step by step toward bounded autonomy.

**What is installed right now:** [docs/STATUS.md](docs/STATUS.md). That file is the only status source; this README makes no version claims.

## Docs

| Read this | For |
|---|---|
| [STATUS.md](docs/STATUS.md) | Installed release, timers, accepted checkpoints, open watch items |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, trust boundaries, deployment model |
| [OPERATIONS.md](docs/OPERATIONS.md) | Runbook: evidence bundle, safe vs typed commands, updating, incident playbooks |
| [DEV-LOOP.md](docs/DEV-LOOP.md) | Offline development: `dev.py`, host evidence, CI |
| [ROADMAP-v0.8.md](docs/ROADMAP-v0.8.md) | R1–R4 plan and future gated actions |
| [AGENTS.md](AGENTS.md) · [SECURITY.md](SECURITY.md) | Rules for coding agents · security rules |
| R4 design: [autonomy1](docs/R4-AUTONOMY1-CONSOLIDATED.md), [proposal/format](docs/R4-PROPOSAL-ONCE-ACTIVATION.md), [install](docs/R4-PROMOTION-AND-INSTALL.md), [schedule](docs/R4-SCHEDULE1-OFF-FIRST-HANDOFF.md) | Current R4 reference |
| [Friends roadmap](docs/FRIENDS-ROADMAP-AND-HANDOFF.md) · [Operations Center roadmap](docs/OPERATIONS-CENTER-ROADMAP.md) · [HTTPS rollout](docs/CH-HTTPS-ROLLOUT.md) | Feature-area references |
| [docs/archive/](docs/archive/README.md) | Historical step docs, old README, TODO and operations logs |

## Develop

```bash
python3 scripts/dev.py test          # whole suite, parallel (~30 s); or: test r4 ui -k schedule
python3 scripts/dev.py check         # what CI runs
```

Work goes on a branch, then a PR to `next`, then CI, then a signed release in `releases/current.json`. The owner installs it with a typed `UPDATE`. Merging never deploys. See [OPERATIONS.md](docs/OPERATIONS.md#updating-to-a-new-signed-release).
