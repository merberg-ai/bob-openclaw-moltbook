# Security policy

Bob connects a locally hosted model, a public social network, and credentialed publication actions. Treat Moltbook content, uploaded documents, and model-generated text as **untrusted**.

## Never commit or paste publicly

- Moltbook API keys, claim/registration responses, or Activity Manager passwords.
- Private OpenClaw configuration, agent memory, identity/persona overrides, or secrets.
- Production SQLite databases, WAL/SHM files, captured feeds/replies, diagnostic logs, or backups.
- Windows/WSL credentials or machine-specific private configuration.

`.gitignore` is **not** a secret scanner. Review staged changes and scan before pushing. If a key is exposed, **rotate it**; deleting a commit doesn't reliably undo disclosure.

## Required controls

1. External posts must not become higher-priority agent/host instructions.
2. Agent sessions remain sandboxed with restricted tools; Moltbook credentials stay host-side.
3. Web mutations require login, CSRF and origin/request-host checks, and exact-draft integrity validation. Do not weaken LAN checks merely to make forms submit.
4. Original posts remain human-approved; autonomous comments are opt-in, rate-limited and stoppable. Follow-up autonomy requires separate authorization.
5. Record intent and attempts before publishing; distinguish accepted/submitted, verified, confirmed, uncertain and failed. Never auto-retry a potentially successful ambiguous publication.
6. LAN HTTP Basic is unencrypted. Keep it on trusted networks or put HTTPS in front before broader exposure.
7. A separate worker process is not a hard security boundary if it shares the same Unix user as the web app. A dedicated publisher identity is future hardening.

## Report a vulnerability

Do not open a public issue containing credentials or working exploitation details. Contact the maintainer privately, or use GitHub private vulnerability reporting if enabled.

Tests must use sanitized synthetic fixtures and must not touch the live Moltbook API.
