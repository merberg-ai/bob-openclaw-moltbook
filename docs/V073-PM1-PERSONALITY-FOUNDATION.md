# PM1 Personality Foundation, first release (`v0.7.3-pm1-foundation1`)

## What this release does

Adds **Bob's Mind · Personality** to the authenticated dashboard navigation at `/mind/personality`. Includes eight responsive 0–100 sliders, divided between social style and intellectual style, with 5-point increments and plain-language descriptions.

- Live, JavaScript-only **interpretation preview** changes as sliders move. This is deterministic guidance, **not an Ollama-generated Bob response**.
- **Save staged profile** stores eight strictly validated values under `bob_personality_*` in the existing private SQLite `publish_settings` table. Values default to the documented suggested initial profile, not assumptions about existing `SOUL.md`.
- **Revision history & Restore profile** preserve full validated snapshots in an additive `bob_personality_revisions` table, with timestamp and SHA-256 integrity hash. Restore creates a new revision; it does not erase history.
- A **read-only OpenClaw workspace inventory** checks `~/.openclaw/workspace/SOUL.md` and `IDENTITY.md` metadata only: presence, byte count and shortened hash. It rejects symlinks and oversized/non-owner files and does not expose or copy their private contents.
- CSRF, same-origin/Host checks, existing LAN authentication, bounded POST size, strict field allowlist and transaction semantics apply to save and restore.

**Important:** This release does **not** apply sliders to active OpenClaw sessions, write to any OpenClaw identity/operating files, call Ollama or Moltbook, alter publishing permissions or start extra workers. The workspace path shown is only the default; the active agent workspace must be confirmed before any PM1 Apply step. OpenClaw's documented `SOUL.md` and `IDENTITY.md` are injected into sessions; overwriting them without reading the actual identity is unacceptable.

## Next PM1 step: safe Apply to Bob

Once this first release is operator-verified:
1. Confirm the actual active OpenClaw main-agent workspace and its existing `SOUL.md`/`IDENTITY.md` content locally without disclosing it to public Git or logs.
2. Implement an **explicit preview diff** and a separate **Apply to Bob** confirmation button that preserves preexisting persona and safety boundaries, creates private backups, writes atomically, detects concurrent edits and supports rollback.
3. Verify that a fresh sandboxed session sees the selected style, with no changes to tool permissions or publication behavior. Never claim sliders have precise psychological meaning.

Only after PM1 is complete should PM2 implement source-linked persistent memories, then Friends Manager FM1–FM3.

## Operator acceptance, one command

`bobctl update`, approve the manifest after reviewing it, then open `http://192.168.1.24:18790/mind/personality`. Move a slider, **Save staged profile**, reload and confirm its number persists. Click **Restore profile** on a previous revision if desired. Check the read-only identity file inventory. **No shell test commands needed**; GitHub CI uses synthetic SQLite and temporary files.

## Release safety

Manifest `v0.7.3-pm1-foundation1` upgrades from operator-installed `v0.7.2-redirects1` with exactly three files: `bob_personality.py`, generated `navigation_shell.py`, and generated `bob-activity-manager`. Only Activity Manager restarts. Existing publisher, scout and original-post workers are unchanged. Existing updater backs up SQLite, checks health and retains rollback support. Synthetic tests ensure no existing protected POST implementation changes.
