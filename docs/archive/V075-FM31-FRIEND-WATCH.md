# FM3.1: individual friend watch preferences and saved Scout observations

**Candidate:** `v0.7.5-fm31-watch1`, upgrading directly from installed `v0.7.5-scout-importfix1`. **One file** (`bob_friend_scout.py`), Activity Manager restart only. Existing Scout/publisher files are untouched.

## Feature

The authenticated **Moltbook → Friend Scout** page now has **Individual friend watch preferences** for up to the first ten active friends. Existing active friends default to **watched** when no preference is stored, preserving FM3 behavior. The owner can **Pause watching this friend / Resume watching this friend** independently of the FM1 relationship, mute, or archive state.

Only when the existing **global Friend Scout switch is enabled** will the next scheduled Scout read public profiles/posts. The original maximum still holds: two friends selected, one public post per friend, at least four global posts. **Muted, archived, corrupt, or individually unwatched entries are never selected.** No timers, new permissions, autonomous follows, direct messages, comments or model tools are introduced.

Watch settings live in two additive local tables within the existing backed-up private SQLite DB:
- `bob_friend_watch_prefs`: one SHA-256 sealed row per modified friend, with optimistic digest, UTC timestamp and version.
- `bob_friend_watch_history`: short immutable watch-change history (no private notes).

Watch changes use the **existing** authenticated dashboard POST handler and CSRF/origin checks, with six exact whitelisted form fields; no new route. The operation validates the current integrity-sealed FM1 friend row and checks both the current friend digest and watch preference digest before writing. Replayed/stale forms fail closed. A corrupt stored watch preference **does not** reset to the permissive default; that friend is excluded from scouting until a separate operator repair. No private memories, relation notes or interests are forwarded to Moltbook.

The **Bob's selected friend discussions** section presents existing **WHY rationales** for source-verified Scout drafts where the **chosen author** belongs to an active saved friend. Each entry independently checks the original record, exact hashed feed, chosen post UUID, and author. It shows only up to ten bounded, HTML-escaped observations and up to three per friend, not every post Bob browsed. They are past model explanations, not confirmed facts, relationship trust, or newly generated interests.

## Import packaging lesson

FM3.1 adds **no new installed Python modules**. It updates the already-managed `bob_friend_scout.py` that is imported by the existing Scout worker, with no need to modify `PYTHONPATH` or create a new worker. The preceding `v0.7.5-scout-importfix1` has been installed by the operator, and the old Scout systemd failure state cleared; the operator's next real scheduled Scout run remains the end-to-end verification.

## Minimal live acceptance

1. In OpenClawLab run **`bobctl update`**, check `v0.7.5-scout-importfix1` → `v0.7.5-fm31-watch1`, one file, type `UPDATE`.
2. Open **Moltbook → Friend Scout**. Every active verified friend should appear with **Watched by Scout**, by default; disabled and archived FM1 friends remain excluded. The global enable/disable switch should still work as before.
3. Click **Pause watching this friend** for one agent and refresh. Confirm **Not watched by Scout** appears, its watch history records the action, and FM1 relationship/notes are unchanged. Click **Resume watching this friend** and verify the reverse.
4. **Bob's selected friend discussions** shows a source-verifiable previous Scout WHY note when a saved friend was actually chosen in a prior run, or the explanatory empty state otherwise. The view does not cause AI inference or network activity.
5. Check the next scheduled normal Scout: only watched active friends are eligible for up to two public profile checks. No automatic publication permission changes. Systemd service success after the previous import fix is a separate live acceptance condition.

## Follow-up

A later FM3.2 could add paginated watchlist management beyond ten entries, one-click read-only focused scans with explicit operator initiation, and autonomous *proposals* for Bob's evolving interests subject to human review. None of those are implied by this release.
