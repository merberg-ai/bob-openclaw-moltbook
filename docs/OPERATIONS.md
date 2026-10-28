# Operations and v0.7.0 baseline checklist

**Do not install from this repository yet.** The first actionable milestone is to capture a reproducible, sanitized baseline from the currently working OpenClawLab host.

## Read-only checks

On the existing OpenClawLab system:

```bash
~/.local/bin/bobctl status
~/.local/bin/bobctl doctor
curl -fsS http://127.0.0.1:18790/healthz
systemctl --user list-timers --all
systemctl --user cat openclaw-gateway.service bob-activity-manager.service
```

Do not paste full live config, environment values, API keys or credentials into an issue.

## Host baseline process

1. Capture the *exact* live executable files, SHA-256 hashes, service files, drop-ins, timers, and SQLite schema version in a private staging location.
2. Make a **SQLite online backup** using `sqlite3.Connection.backup()` and verify it. Preserve all publishing states, reviews, quotas and verification records.
3. Compare host files to the v0.6 reference bundle and later fixes; record differences without overwriting the host.
4. Select canonical sanitized source and test fixtures, removing secrets, machine-specific settings, memory, personal data and logs.
5. Run legacy v0.5/v0.6 regression tests including the LAN `Origin: null` request case, CSRF checks, and comment/original publication paths against temporary databases.
6. Add version identifiers and a reproducible CI test suite. Tag the verified baseline **only after** acceptance.
7. Implement and demonstrate `bobctl update --dry-run`, pinned-release update and rollback in staging before touching production.
8. During a real upgrade, preserve current auto-mode decisions and avoid surprise publish actions.

## Mandatory acceptance gates

- LAN and localhost login, approvals, rejections and autonomous toggle work; no CSRF regression.
- Scouting and original generation produce source-validated data, not fabricated post IDs.
- Worker states, challenges and ambiguous results are preserved; uncertain publication requests are not blindly retried.
- Approved original posts still need an explicit Publish action.
- Reboot recovery, Docker sandbox restrictions, Gateway readiness and Ollama integration remain stable.
- An operator can stop/pause autonomous activity and have that decision respected.
- Rollback restores running code safely without discarding new database writes.

## Future operations commands

Planned, **not yet implemented in this repository**: `bobctl version`, `bobctl check-update`, `bobctl update --dry-run`, `bobctl update`, `bobctl rollback`.

Use versioned releases, content checksums, durable backups, additive migrations, atomic deployment and health checks. Never pipe mutable `main` directly into a production shell.
