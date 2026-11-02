# TODO (forward-looking only)

Done items go to [docs/STATUS.md](docs/STATUS.md) as accepted checkpoints. The full historical log, through 2026-11-02 morning, is [archived](docs/archive/TODO-log-v0.8.md).

## Now: cleanup and dev loop (source only, nothing installed)

- [x] Phase 0: `scripts/bob_evidence.py`, `scripts/dev.py`, CI simplification, host-coupled test fixes (PR #150)
- [x] First natural R4 tick observed and accepted (2026-11-02 09:02, `skipped/bob_abstained`)
- [ ] Phase 1a: docs consolidation (`STATUS.md`, new README/ARCHITECTURE/OPERATIONS, archive)
- [ ] Phase 1b: archive one-off scripts and their tests that no current release, updater or CI path needs
- [ ] Phase 1c: single release-ID source shared by updater, installed gate and schedule (unknown IDs still fail closed)

## Next: Console v2 (one signed release)

- [ ] Real-source manager (no patch chain) with a route table, same TLS/auth/CSRF on :18790
- [ ] Push-only `wss://` channel: ticket plus Origin/Host checks, bounded clients and frames, one shared state hub
- [ ] Self-hosted JetBrains Mono / Space Grotesk / Orbitron; glass cards; strict CSP with no inline styles
- [ ] Sections: Now · Inbox · Bob · Activity · Controls · System. Desktop sidebar with Ctrl-K, mobile bottom tabs, 380 px usable
- [ ] `/classic/…` keeps every legacy page until it is ported
- [ ] `dev.py preview` (synthetic DB, fake systemd) and Playwright screenshots at 380/768/1440 in CI

## Watch (see STATUS.md)

- [ ] R3 `decision_invalid_model_json` recurrence. If it recurs, port R4 `format1` prompting to R3.
- [ ] R4 vs publisher start collisions. If frequent, add a bounded re-check.
- [ ] Explain 14 `queued` publish jobs and 8 `queued` R3 proposals.

## Later (roadmap, not authorized)

- [ ] Evidence-backed social context (FM4.2/4.3), revisable impressions with owner corrections
- [ ] Per-action public enablement, one category at a time, each with its own review and typed opt-in
- [ ] CH1 real Chat with Bob through a server-side loopback Gateway adapter
- [ ] Fresh-host installer that reuses existing OpenClaw/Ollama
