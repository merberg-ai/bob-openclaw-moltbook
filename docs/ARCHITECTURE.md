# Architecture and trust boundaries

## Existing host installation (not yet imported)

- **Windows host:** Ollama runs a local model; Windows also starts Docker Desktop and the dedicated WSL2 distribution.
- **OpenClawLab WSL2:** OpenClaw Gateway and a tightly restricted Docker agent sandbox; the Gateway is normally loopback-only.
- **Host-side scout:** Fetches bounded Moltbook feeds, prepares sanitized untrusted snapshots, asks Bob for a choice/draft, and verifies chosen IDs against the captured source.
- **Activity Manager:** Lightweight Python HTTP service with authenticated LAN option, local review and publishing controls, and CSRF/origin/draft-integrity guards.
- **Credentialed publisher:** Separate host-side worker with Moltbook API access and a persistent submission ledger. Optional auto-comments require eligibility and quotas. Original posts require explicit approval.
- **Storage:** Private SQLite activity database, publication jobs and replies, captured feed snapshots, validated drafts and event history.
- **Lifecycle:** systemd timers and services; Windows startup and WSL recovery orchestration.

These are *descriptions* of the host as previously tested. **The exact running versions, files, patches and service units must be inventoried for v0.7.0 before a source import or deployment.**

## Untrusted data flow

```text
External Moltbook feed (untrusted)
  -> bounded sanitized snapshot
  -> sandboxed agent (no Moltbook credentials)
  -> structured, validated draft with source provenance
  -> operator approval OR eligible separately enabled auto-comment rule
  -> host-side credentialed worker
  -> Moltbook submission / verification / public confirmation
  -> persistent job ledger and reply monitoring
  -> authenticated Activity Manager
```

Untrusted source text cannot update `SOUL.md`, `IDENTITY.md`, privileges, system instructions, tools, configuration, or credentials. Learned observations and opinions will live in separate lower-trust stores.

## v0.7 target modules

```text
src/
  bob_manager/       # app, page routes, security, templates, CSS, JS
  bob_workers/       # scout, publishing, originals, reflection, conversations
  bob_core/          # database, additive migrations, jobs, observations, opinions
deploy/
  systemd/
  windows/
scripts/             # install, update, backup, rollback, doctor
tests/               # isolated synthetic regression tests
docs/
```

Keep the existing executable names, service units and schema compatible while migrating. Release code should be staged and tested before an atomic switch. Never treat process running as proof that Gateway/Ollama/Docker are ready.

## Deployment limitations and safety

- An HTTP Basic LAN login is not encrypted without TLS.
- Sharing a Unix account between a dashboard and publisher isn't OS-level isolation.
- WSL may need Docker/Ollama readiness and startup retries after Windows sign-in.
- Auto-comment settings are not authorization for autonomous original posts or conversational follow-ups.
