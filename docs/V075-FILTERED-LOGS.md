# v0.7.5 Logs & Diagnostics

**Release:** `v0.7.5-logs1`, upgrading directly from operator-tested `v0.7.4-fm3-friend-scout2`.

## Why this exists

The user reported Scout showing **failed** in systemd while Comment publisher displayed a **failed** checkpoint, with a failed comment job around `2026-10-30T00:05:13Z`. Prior Overview displays states but not the underlying safe diagnostic reason. A **failed worker** is not necessarily evidence of a failed public post; in particular FM3 blocks auto-comments targeting known friends as a safety feature. The actual cause for this OMEN cannot be established from the screenshot alone.

## Delivered

The authenticated Activity Manager now has a first-class **Logs** link in the sidebar at `/logs`. It is a GET-only, no-JavaScript, responsive diagnostics page with server-side filters for:

- **Service:** All, Scout, Comment Publisher, Original Drafting, Original Publisher, Activity Manager, Gateway.
- **Severity:** All, Error, Warning, Info.
- **Source:** All, Jobs, Journal, Events, Checkpoints.
- **Window:** 24 hours, 7 days, 30 days (in UTC).
- **Search:** Up to 80 characters of a safe diagnostic message, job/run ID or service.
- A clear-filter link, matched-entry count, times in UTC, and a cap of 120 newest matched rows.

The page reads only existing sources:

1. **SQLite:** already recorded `publish_jobs.last_error` (and status), original post failures, original generation errors, `publish_events`. The existing queue DB is opened in SQLite **read-only mode** with `PRAGMA query_only=ON`, with separate bounded queries for each known table.
2. **Worker checkpoints:** existing `job-progress/*.json` from `bob_job_tracking.read_checkpoints`. No raw text/secret fields enter its checkpoint format.
3. **User-systemd journal:** bounded, read-only `journalctl --user --unit <one of six fixed service names> --since <validated UTC window> --no-pager --output=json --quiet --lines 180`. It uses subprocess **without a shell** and a 3-second limit. All service names are an internal allowlist. The page never runs dynamic commands or retrieves the system journal or arbitrary units.

## Privacy/security boundary

This is **not a raw log viewer**. Real logs can contain Moltbook post text, prompts, API tokens, private filesystem paths, exception messages, headers or credentials, even when emitted accidentally by third-party code. Therefore **only allowlisted diagnostic reason categories** and sanitized journal patterns are shown. Unknown raw errors and arbitrary journal messages are withheld. Selected HTTP codes, known validation failures, process exits, timeouts, queue safety blocks, standard timestamps and safe opaque run IDs are retained. Event `details` are never printed verbatim.

A visible note explains when queue DB or journal are unavailable. Journal availability can depend on how the Activity Manager systemd user service is configured. The browser never receives the raw journal payload, only safe derived messages. As in prior releases, LAN HTTP Basic is not transport encryption; keep Activity Manager private on LAN/VPN or use a separately hardened HTTPS proxy for sensitive administrative telemetry.

There are **no** schema migrations, worker changes, daemon restarts other than Activity Manager, new timers, new permissions, credentials access, automatic retries, publishing actions, Scout changes or changes to the FM3 friend guard.

## Single-command installation

From OpenClawLab WSL run:

```bash
bobctl update
```

Verify `v0.7.4-fm3-friend-scout2` → `v0.7.5-logs1`, three files (new `bob_diagnostic_logs.py`, generated `bob-activity-manager`, generated `navigation_shell.py`) and an Activity Manager restart. Confirm by entering `UPDATE`. The existing updater keeps its checked database backup and code-only rollback.

## Browser acceptance

1. Open **Logs** in the dashboard sidebar. Confirm the page loads without JavaScript and shows records or an explicit unavailable-source indication.
2. Filter **Service: Publisher**, **Severity: Error**, **Source: Jobs**, **Window: 7d**. The reported failed comment job should appear if retained in the private SQLite queue. Search its run ID `20261029T224411Z` to isolate it. Check the safe error reason and timestamp.
3. Select **Service: Scout**, **Source: Journal**, **Severity: Error**, **Window: 7d**. If the systemd journal is available to the current login, a service exit or sanitized Scout error should explain the failed service. If the journal isn't accessible, the page should explicitly say so.
4. Change to **Source: Checkpoints** to cross-reference worker timestamps. Use **Clear filters** to return to the overview.
5. Confirm **Scout & review**, **Friend Scout**, **Memory**, **Friends**, and **Discover** remain functional. No page action should start/retry any Scout or publication worker.

## Follow-up investigation

Read the actual **sanitized job reason** before deciding whether this is an operational failure or intended FM3 safety behavior. Failed job states must not be retried blindly: a network publish attempt can be **uncertain** even if the platform received it. The system already distinguishes an uncertain network write from a failed preflight or a blocked automatic friend reply. A future logs phase may add restricted operator-authenticated export or log correlation, but deliberately does not expose raw logs on private HTTP or write new log collectors.
