# PM1.3 — Personality confirmation UI and archived queue actions

**Release candidate:** `v0.7.3-pm1-uiqueue1` from verified `v0.7.3-pm1-apply1`.

## Scope
- Theme PM1 Apply and Roll Back text inputs using the Personality Lab's dark controls, focus outline, responsive widths, and spaced form layout.
- In **Manage queues**, archived items are now selected into their own **Restore selected archived** form, even when visibility is **All**.
- Active items remain in the ordinary Approve/Reject/Queue/Archive form. Remove **Restore** from that form's operation picker, which previously made the wrong selection possible.
- Archived-only views show the Restore action; active-only views show normal bulk actions. All views retain the same filters and pagination.
- Existing `apply_batch` backend checks remain untouched: archived drafts cannot be approved/rejected until restored, stale fingerprints are refused, and queue publication is still explicit and bounded.

The restore action changes only the dashboard's hidden-item state. It does not approve, reject, queue, or send content. Restoring an auto-queued item does not cancel or duplicate its existing publication job.

## Release
Only these three installed library files change:
- `bob_personality.py`
- `bob_personality_apply.py`
- `bob_dashboard_manage.py`

The updater preserves existing credentials and data, takes its usual private backup, and restarts the Activity Manager only. It does not start publisher/scout workers or alter `SOUL.md`. OpenClaw Gateway and Ollama are unaffected.

## Acceptance on the existing operator host
1. Run `bobctl update --check`, then `bobctl update` if the proposed release is `v0.7.3-pm1-uiqueue1` from `v0.7.3-pm1-apply1`. Confirm by typing `UPDATE`.
2. Visit **Bob's Mind → Personality**. Apply/rollback confirmation inputs should match the dark theme and buttons should have visible spacing on desktop and mobile. The already-applied profile is unaffected by the upgrade.
3. Visit **Manage queues → Scout & review**, filter **Pending** and **All** visibility. Archived rows should be selectable only for **Restore selected archived**. Active rows remain selectable for Approve/Reject.
4. Restore an archived **test item** only if you actually want it returned to the active review list, then use the ordinary review controls. No publication occurs unless independently queued/published through the existing guarded workflow.
5. Confirm that active-only and archived-only visibility filters each show only relevant actions.

All CI tests use synthetic in-memory SQLite. No live post, worker, credential, host service, or private identity file is modified by the pull request.
