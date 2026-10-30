# OC3: Sanitized Diagnostic Console

**Candidate release:** `v0.7.6-oc3-console1`, upgrading from operator-accepted `v0.7.6-oc2-automation1`. **Not installed or accepted on the OMEN until the operator runs `bobctl update` and confirms the LAN UI.**

## What's new

A **Console** tab joins the authenticated Activity Manager navigation. It's a compact, terminal-inspired, **read-only diagnostic viewer**, not a shell. It combines the *existing* Logs classifier's bounded, sanitized SQLite job/event observations and enumerated worker-stage checkpoints with current local Gateway, Ollama, Scout timer, publisher timer and Activity Manager readiness probes.

You can filter **service**, **severity**, **source**, **24h/7d/30d** time window, and short safe message/job ID search. The default **Local + health** stream returns up to **80** observations, sorted newest-first. It deliberately **does not call journalctl**: polling every 45 seconds for journal across services would make the LAN dashboard needlessly slow. To inspect classified systemd evidence, explicitly choose **Journal**; the existing Logs module restricts journalctl to fixed allowlisted user services, a bounded timeframe, a maximum line count and result bytes, with no shell. **Journal mode never auto-polls.** Ollama is not assumed to be a user systemd service, so it appears through a loopback readiness probe, not an invented log source.

Controls: manual **Refresh now**, **Pause updates / Resume updates**, **Auto-scroll**, **Copy safe lines**, and **Export safe text** (generated server-side from the *same* sanitized bounded entries). Background polling pauses while the document is hidden; refresh errors say the snapshot may be stale. The HTML is escaped server-side; live rendering uses `textContent` and safe DOM methods, not `innerHTML`. No prompt contents, friend notes, messages, raw journal entries, credentials, model outputs, arbitrary exception text or unrestricted filesystem access are provided. A readiness observation does not establish that Bob is thinking, posting or interacting.

## Security/compatibility

- New `bob_diagnostic_console.py` module; a pinned OC2-derived builder adds only three **authenticated GET** routes (`/console`, `/api/dashboard/console`, `/assets/bob-console.js`) and one navigation link. Only the Console page joins the existing CSP same-origin script allowlist. All prior login, Host/Origin/CSRF checks, publication/approval handlers and existing features remain byte/AST-identical.
- JSON/text endpoints accept bounded query strings with strict allowlisted filters; no user-provided executable command, systemd unit, URL, path or browser-side privileged action.
- Default stream reuses sanitized collector logic and fixed local status probes; intentionally no automatic journal requests. Journal is opt-in and bounded by `bob_diagnostic_logs.py`'s allowlists and redaction.
- The updater installs **three files**: new `bob_diagnostic_console.py`, generated `bob-activity-manager`, generated `navigation_shell.py`. Only Activity Manager restarts, with prior backup/rollback intact.
- Synthetic `tests/test_oc3_diagnostic_console.py` verifies private-data redaction, malformed filters, source/time filtering, fixed-host/systemd journal allowlists, missing-dependency honesty, safe escaping, read-only update, and exact protected POST/auth handler equivalence. Full CI required before merge.

## Operator acceptance

1. In OpenClawLab run `bobctl update`; confirm `v0.7.6-oc2-automation1` → `v0.7.6-oc3-console1`, type `UPDATE`.
2. In your authenticated LAN dashboard open **Console**. The default stream should show safe service readiness and any stored local jobs/events/checkpoints without requiring a shell.
3. Try **Error** severity, **Publisher** service, and **Journal** source (manual Refresh). Some filters may legitimately show no entries. No raw secrets, prompts or unchecked stack traces should appear.
4. Check Pause/Resume and Auto-scroll; test **Copy safe lines** or **Export safe text**. On an HTTP LAN browser clipboard access may be restricted; Export safe text is the fallback.
5. Confirm other Automation/Overview pages and existing original-post/manual queue controls still work. **Do not generate/publish a test comment solely to accept the Console.**

**Next:** OC4: one-view deterministic **Why no activity?** investigator and durable, sanitized worker skip-reason events. FM4/FM5 remain on hold. No new automation or posts authorized by OC3.
