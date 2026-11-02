# v0.7.1 production release contract (DESIGN ONLY)

Status: **NOT APPROVED, NOT DEPLOYABLE**. The operator confirmed 163 offline tests and the combined isolated HTTP/rollback acceptance. This is the boundary between validated candidate code and a future production change.

## Known live facts, verified by operator

- Installed Activity Manager SHA-256 matches pinned original `9f75535bc013c9ea7ab7582e0adfad3e78d6a7ce769a5b14c66b949c5542e65c`.
- Existing service is loaded, running, and references the manager executable directly.
- Existing unit has drop-ins, an explicit working directory and inline environment.
- Unit source inspection found no EnvironmentFile, ExecStartPre, ExecStartPost or ExecCondition directives; this is a *source inspection*, not exhaustive proof of effective settings.
- Recent private SQLite backup passed integrity verification at prior host preflight. **Freshness must be rechecked immediately before deployment**.
- Generated v0.7.1 candidate is a pair: `bob-activity-manager` and `navigation_shell.py`; the review ZIP has `deployable: false`.

## Production installer requirements

1. **Fail closed** if the installed manager SHA differs, service topology has drifted, a required file is a symlink, the operator lacks permissions, or the private verified backup is stale.
2. Stage both candidate files to a unique, private versioned directory. Verify content digests, ownership and import resolution before any service change. Preserve original executable and all live state.
3. Work out a **reviewed effective systemd launch contract**, including drop-ins, working directory, inline environment, user scope, and Python sibling module import. An unrelated `current` symlink cannot redirect the current directly referenced executable.
4. Implement a single-writer lock and durable recovery marker so an interrupted update cannot leave an ambiguous partially applied release.
5. Provide dry-run diagnostics that report only non-sensitive pass/fail classifications. No raw `ExecStart`, environment, config files, credentials or database records in logs.
6. Before live switch, document exact service impact, whether a brief dashboard outage is expected, and ensure timers/workers/publishing semantics are unchanged. Do not pause or restart unrelated services merely to update UI.
7. Require **separate, explicit operator approval** for the production install/restart, distinct from acceptance of this document or test run.
8. After switching, use bounded service health verification plus loopback HTTP routes, Basic auth/Origin/CSRF checks in a safe manner, and evidence the new navigation module actually loaded. Failures trigger **code-only rollback** to the exact original release and a second health verification. Never restore old SQLite over newer writes automatically.
9. On failure to restore health, stop and surface a local actionable incident without attempting repeated restarts or publishing. Preserve evidence without leaking secrets.
10. Prove complete behavior first with synthetic service fixtures in a disposable environment and a controlled failed-health simulation. CI passing alone does not prove the OMEN deployment.

## Release decision

- Visual UI acceptance: **YES**.
- Offline regression and isolated HTTP runtime acceptance: **YES (163 tests, operator reported)**.
- Actual installed service switch, authenticated LAN regression and restart/rollback: **NOT YET TESTED**.
- Permission to deploy: **NOT GRANTED**.
- Main branch merge: **NOT REQUESTED**.

**Do not copy the review ZIP into live executable paths or modify service units as a shortcut.**
