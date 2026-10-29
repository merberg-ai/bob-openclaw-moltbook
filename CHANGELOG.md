# Changelog

## v0.7.2 — Deployed (operator confirmed October 29, 2026)

- Responsive desktop/mobile multi-page Activity Manager, secure Settings password change and trusted-console login reset.
- Live 15-second System Status with real worker checkpoints, stale/unknown handling, bounded error summaries and authenticated API.
- Scout, comment publisher, original generation and original publication stages reflected without fake percent progress.
- Original-thought drafts accept strictly structured variants of title/body output while preserving content validation and human approval.
- Comment-verification responses without confirmed IDs remain `verified_unconfirmed`; public visibility is not inferred from an API success response. Added a bounded read-only public comment audit.
- Manual comment approvals take queue priority over automatically generated comments. Existing **two attempts per UTC day**, one-hour minimum spacing, and no-automatic-retry safeguards remain unchanged.
- The operator verified a successful original-thought draft, four Moltbook-visible published comments, and a clean four-test manual-first publisher update.

## v0.7.2 — Update infrastructure

- Implemented `bobctl update` and a verified one-time bootstrap for the existing host. The operator installed the bootstrap successfully and observed an up-to-date status.
- Merged the working v0.7.2 development branch to `main` via [PR #5](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/5).
- Prepared a guarded migration of the installed updater from `feature/v0.7.1-navigation` to the canonical `main` checkout, with a private registry transition and code/config rollback. **The migration is not yet verified on the host.**
- Prepared a no-op `v0.7.2-main-channel` release manifest. The first nonempty manifest-driven update remains to be tested with upcoming dashboard improvements.

## v0.7.0–v0.7.1 — Historical foundation

- Imported and reviewed sanitized host source with private inventory and verified SQLite backup tools.
- Implemented guided responsive navigation, release rehearsals, version-pinned production upgrades, health probes and code-only rollback workflows.
- Preserved Moltbook credentials, approval records, publication history and original-post consent boundaries outside GitHub.

## Not yet implemented

- A supported clean-host installer for Windows/WSL/OpenClawLab.
- v0.7.3+ evidence-linked learning, evolving opinions, reflective memory and multi-turn conversation continuity.

See [operator guide](docs/OPERATIONS.md), [main-channel migration](docs/MAIN-UPDATER-MIGRATION.md), and [installation status](docs/INSTALLATION-STATUS.md).
