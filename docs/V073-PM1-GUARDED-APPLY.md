# PM1.2 — Guarded personality Apply & Roll Back

**Candidate**: v0.7.3-pm1-apply1, from operator-verified v0.7.3-pm1-csp1.
**Deployment**: Not installed until the operator runs \`bobctl update\`.

## What it changes

Adds a verified **Apply personality to Bob** section to the existing
\`/mind/personality\` dashboard. The editable sliders still need **Save staged
profile**. A separate preview shows only the exact new/changed managed section
of \`SOUL.md\`, not the rest of Bob's personal identity.

**Apply to Bob** is protected by existing LAN authentication, CSRF token,
same-origin POST validation, bounded form fields, a deliberate \`APPLY BOB\`
confirmation, SHA-256 hashes of both the saved profile and the inspected
\`SOUL.md\` content, and a private file lock.

The active \`main\` agent's workspace is resolved using documented read-only
\`openclaw agents list --json\` and checked to be under the operator's home.
If the CLI is unavailable, output is malformed, no unique main agent exists,
or \`SOUL.md\` is absent, symlinked, hardlinked, not owner-controlled, oversized
or invalid UTF-8, the Apply button **does not appear**. A reason appears in the
dashboard. It will not silently guess \`~/.openclaw/workspace\` is active.

### Write and rollback safety

- Only a delimited \`BOB_PERSONALITY_STYLE_V1\` section is inserted/replaced.
  All existing text outside that block is preserved byte-for-byte.
- Before any edit, the original exact bytes are saved under
  \`~/.local/state/bob-personality/<random-id>.soul\`, private mode 0600.
  A short manifest in this private directory captures before/after SHA-256,
  agent workspace, status and time. No contents or credentials go to Git.
- Atomic same-directory replacement and fsync preserve original file mode.
  No new persona instructions are mixed into \`IDENTITY.md\` or \`AGENTS.md\`.
- The rollback form requires \`ROLL BACK\` and only restores the verified
  previous version when the current \`SOUL.md\` still matches the exact hash
  written by Apply and the private backup matches the original checksum.
- A concurrent edit, partial/duplicate managed section or unexpected workspace
  change **fails closed**; a backup is retained if an error occurs.
- Other code and publishing permissions are not modified. Old agent sessions
  may retain their earlier prompt; a fresh OpenClaw session is needed to
  observe the changed style. No fake claim is made about retraining or precise
  trait percentages.

## Operator acceptance (no test-command marathon)

1. Run \`bobctl update\`, review the three-file manifest and approve.
2. Open the dashboard **Bob's Mind → Personality**. Save your preferred
   sliders first if you haven't already.
3. Inspect the **Apply personality to Bob** preview. If it shows
   **Apply unavailable**, the active workspace could not be verified;
   **do not bypass the guard**.
4. When verified, type \`APPLY BOB\` and press Apply. Refresh the page;
   the plan should show **Already applied**, with **Restore previous SOUL.md**
   available.
5. For a rollback test, type \`ROLL BACK\`, submit and refresh. The managed
   change is removed/restored exactly to its previous state.

GitHub CI runs isolated synthetic SQLite and temporary-workspace acceptance
checks including original-byte preservation, reapply, rollback, stale-preview
refusal, missing OpenClaw main workspace, bad markers, symlink/hardlink safety,
and unchanged existing dashboard approval/publishing handlers.

No explicit update to the actual live agent has happened through a GitHub
merge. These file operations only take effect after the operator confirms
them on the authenticated dashboard.
