# Installation status and supported release paths

**Checked October 29, 2026.** The operator has verified an existing OpenClawLab installation running Bob v0.7.2 with the updated Activity Manager, mobile Settings, status stages, original-thought drafting, and Moltbook publishing. The operator successfully installed `bobctl update` and received `up to date (v0.7.2-updater-bootstrap)`.

## What works today

| Workflow | Status | What it does |
| --- | --- | --- |
| `bobctl update --check` | **Verified by owner** | Confirms the installed GitHub release registry and checks for an available manifest |
| `bobctl update` | **Installed, basic check verified** | Prompts for approval for future manifest-driven releases. A **nonempty** manifest release has not yet been exercised end-to-end on production |
| Existing-host upgrades through historical scripts | **Used successfully for v0.7.1/v0.7.2** | Exact-match checks, SQLite backup, staged code swaps, rollback/health checks |
| `scripts/bootstrap_bob_updater.py` | **Verified on owner's existing host** | One-time registration of known-good v0.7.2 code and installation of the updater command |
| Fresh Windows/WSL/OpenClawLab installation from a clone | **Not implemented or verified** | There is no supported unattended/new-host setup installer |

## Why this is not a clean installer yet

Existing release scripts and the updater depend on **preexisting state**: OpenClawLab WSL2 distro, ordinary `openclaw` user, Docker/OpenClaw/Ollama and local model, systemd user services/timers, a private credentials file, an existing application database and startup recovery configuration. Their guards deliberately refuse arbitrary unknown hosts rather than secretly creating users, generating tokens, exposing API credentials or starting autonomous publication.

The v0.7.1 end-to-end systemd install document describes a **disposable rehearsal**, not a production clean-install procedure. Its old blocker descriptions are historical: v0.7.1 production upgrades were subsequently deployed, but the new-host installer gap remains.

## Proposed real installer: separate next milestone

A production-ready clean installation should have one guided command and explicit steps for:

1. Windows/WSL2, Linux user, systemd and local port prerequisites; clear failure messages without modifying an existing host.
2. Local Ollama and OpenClaw/Docker preflight; model selection and private dependency installation, with user consent before downloads or external services.
3. Owner-private Moltbook credentials and dashboard username/password setup, without exposing them in shell history, logs or Git.
4. Database creation and the initial protected application files, user systemd services/timers, and Windows reboot/startup recovery, with activation **off by default** until reviewed.
5. Authenticated dashboard health, read-only worker readiness and a one-step rollback/uninstall that preserves private data and never automatically posts.
6. One fresh-environment acceptance on a disposable OpenClawLab VM/WSL distro, not just synthetic tests.

A clean installer must **never** run the old v0.7.1/v0.7.2 pinned update scripts on an unrecognized installation.

## Git branch transition

The installed updater currently pins its GitHub checkout to `feature/v0.7.1-navigation`. Merging that branch into `main` does not switch the already installed updater or the checked-out working branch. We should move new release authoring to `main` and migrate the updater's trusted checkout/branch in a **separate, explicit, guarded update**. Don't delete the feature branch while production is still pinned to it.
