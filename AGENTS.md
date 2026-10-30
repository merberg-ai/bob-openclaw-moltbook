# Bob v0.8: rules for coding agents

This file governs new v0.8 engineering on `next`. **Do not silently change the working v0.7 installation on `main`.** Read [the adopted roadmap](docs/ROADMAP-v0.8.md) before proposing architecture or releases.

## Safety and decision architecture

- The real existing OpenClaw **main** agent proposes actions via an isolated decision session. Do not create an independent second Bob personality.
- One action contract, one centralized policy evaluator and one event ledger. All future external actions must pass validation, policy, **atomic reservation** and a final just-before-send recheck. A pure policy verdict alone is not a publishing authorization.
- Moltbook input, model output and saved text are **untrusted data**. Never pass them to shell commands, paths, URLs, SQL fragments, release configuration or high-priority instructions.
- Moltbook credentials remain exclusively in the host publisher. The model, shadow package and dashboard do not read them.
- R2 is SHADOW ONLY: no Moltbook writes, no publishing queue writes, no new automatic follow, upvote, comment, reply or original-post authority. New actions start Off or Propose and must have separately authorized controls.
- Trustworthy evidence distinguishes **observed**, **drafted**, **queued**, **attempted**, **acknowledged**, **publicly verified**, **received reply**, **tentative opinion** and **operator-reviewed memory**. Never infer a social relationship from a local Friends directory entry.
- Never silently overwrite PM2 curated memory, FM4.1 evidence, owner corrections, agent identity or `SOUL.md`.

## Install and dashboard

- R1 accepted live baseline is `v0.7.8-updater2`, installed after a verified catch-up from `v0.7.6-oc41-polish1`. Current `main` stays the rollback/stable source. New work merges through PRs to `next`.
- Do not alter `releases/current.json` for unfinished internal work. Complete R2's versioned installer, backup/migration/recovery contract and shadow acceptance gate before releasing `v0.8.0-shadow1`.
- Dashboard structure: Now, Inbox, Bob, Controls, Diagnostics link; reserve Chat as a separate future route. 380px usability. New displays consume centralized events; no bespoke permission toggles.
- Never add more `scripts/build_v07*_candidate.py` source patchers for new features; use real source modules and templates. Historical builders remain only for existing release/rollback dependencies.

## Development

- Full offline/synthetic tests and GitHub CI before merge; no live Moltbook, model or systemd writes in CI. Real-host probes require explicit owner authorization and are separate from offline tests.
- Prefer meaningful integration PRs and only **four owner-facing release checkpoints** (R1 done, R2 shadow, R3 guarded cutover, R4 social/UI), rather than repeated micro-installs.
- No release cutover or branch switch simply because a GitHub commit exists. Existing `bobctl update` backups, hashes, typed confirmation, manifest chain and rollback are mandatory.
- Keep living docs accurate. Avoid version claims contradicted by `releases/current.json` or the last operator-confirmed installed registry.
