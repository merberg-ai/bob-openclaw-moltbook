# PM2.1 — Memory edit feedback and form repair

**Release:** `v0.7.3-pm2-editfix1`, upgraded from deployed `v0.7.3-pm2-memory1`.

## Operator report
A memory-edit POST returns a generic **Memory unchanged** HTTP 409 page, followed by an unrelated “No review decision was changed” paragraph and without the actual reason. The original backend swallowed all validation exceptions into a generic message. Memory edits were also rejected for unchanged content or an edit reason shorter than eight characters, but the UI did not explain these requirements.

The exact reason for the reported request is unknowable from the screenshot because it was discarded by the server.

## Fix
- A memory-edit form uses **Save edit** or **Correct memory** buttons. Only the clicked button submits a single `operation` field. No duplicate/hidden operation field exists in edit mode.
- Reason is required but can be any nonempty text up to 240 characters. At least one of title/content/category/confidence/source must actually change to create a new revision.
- The authenticated validation-error response now shows a **fixed, whitelisted** user-facing reason, such as `No memory changes to save`, `Edit reason must be 1-240 characters`, `Memory changed; reload before editing`, or an invalid source URL message.
- Unexpected errors, database errors or unrecognized messages remain generic. Never echo submitted content, SQL internals, untrusted source text, file paths or secrets.
- The generic legacy error template is altered **only for /mind/memory** to show “No memory change was saved” and return to the Memory Manager. Scout/Personality/Settings messages and links remain unchanged.
- Source data, current stored memories, revision history, publication records, identity, auth/CSRF/origin guards and workers remain untouched. This is not a database migration.

## Installation and acceptance
1. On OpenClawLab, run `bobctl update` and verify it proposes `v0.7.3-pm2-editfix1` from `v0.7.3-pm2-memory1` (two files, only Activity Manager restarts). Approve by typing `UPDATE`.
2. Open **Bob's Mind → Memory**, select an existing note, edit a field, add a brief reason like `fix`, and click **Save edit**. Confirm the revision increments.
3. Edit that note again, change the inaccurate detail, supply a reason, and use **Correct memory**. Confirm the revision history records the correction separately.
4. Submit without changing any actual memory field. The page should explain **No memory changes to save**, with a return link to the Memory page.
5. Try an invalid public source URL, if desired. The error should explain that an ordinary public HTTPS URL is required. No password, private memory body or SQL details should appear.
6. Check Scout review and Personality are unchanged.

GitHub CI runs synthetic offline tests without touching live agent, user SQLite, network, Moltbook or service processes.
