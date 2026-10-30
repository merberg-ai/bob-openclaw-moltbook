# FM3.2d: opt-in, verified public focus for a watched friend

**Release:** `v0.7.5-fm32d-focus1`, upgrading directly from operator-confirmed `v0.7.5-fm32c-localideas1`. This completes the agreed FM3.2 increments. FM4 and FM5 are **on hold** at the user's request pending other problems and a separate feature.

## Scope

The authenticated LAN **Moltbook → Friend Scout** watchlist offers an **Inspect public activity** expandable action for an active, integrity-checked saved friend. This action is available only with the **global friend scouting switch enabled** and that friend's individual watch preference enabled. The owner must type the exact `INSPECT PUBLIC ACTIVITY` confirmation. Nothing runs on GET/page load or on a timer.

One explicitly requested inspection performs at most **three anonymous HTTPS GETs to the existing pinned www.moltbook.com host**: a public profile lookup using a validated agent handle, followed by up to **two** ID-verified public posts referenced by that same profile. No redirects, credentials, cookies, friend notes, Moltbook writes or arbitrary URLs. The profile-reported handle/UUID must match; each accepted post ID, author handle, and optional author UUID must match. A matching API response establishes **only what that response reported**, not the person's actual identity, account ownership, friendship, agreement or real-time presence.

The bounded public snapshot is stored in the existing backed-up private SQLite DB with a SHA-256 record seal, time, request status and source post IDs. Only two post titles and short excerpts, plus a bounded public profile description, are retained. If verified posts exist, an **optional local** Ollama generation (same fixed-loopback FM3.2c controls) can produce at most one tentative reaction grounded in the first included public post. The local model never receives FM1 operator notes, PM2 memory or platform credentials. Failure/no interest does not block the read-only snapshot.

A local **Approve / Reject / Reopen reaction** review is explicitly owner-triggered, with optimistic integrity digest and local immutable review history. Review records a private decision only: no additional friend directory changes, identity changes, PM2 memory, Scout ranking, new timer, follow, DM, comment or auto-publication.

## Request budget and recovery

- At most **one in-flight inspection globally**.
- At most **six inspections in a rolling 24-hour window**, separated by **at least 15 minutes globally**, and **at least six hours for the same friend**. Failures count toward cooldowns. Maximum **100 stored inspection jobs**, with older entries inaccessible for new requests once full; this is a conservative retention boundary for future work, not automatic pruning.
- One confirmed owner POST includes existing CSRF, same-origin/Host checks and only six fields; any changed friend or watch preference invalidates the request. A pause/global disable/mute during fetching causes results to be discarded.
- Jobs stale over three minutes are failed on page view, without automatic retries.
- Existing Friend Scout opt-in, watched-friend cap for scheduled Scout, manual-only friend-targeted publishing, and prior AI review controls remain unchanged. The new feature does not schedule any autonomous social reads.
- Updater modifies **two managed files**: existing `bob_friend_scout.py` and generated `bob-activity-manager`; no new installed library, timer, systemd unit, tool or privilege. The builder makes only a verified manager import and post-commit worker launch change. `bobctl update` uses existing backups and guarded rollback.

## Acceptance

After offline CI passes and the PR is merged:
1. In OpenClawLab run **`bobctl update`**. Confirm `v0.7.5-fm32c-localideas1` → `v0.7.5-fm32d-focus1`, review two-file proposal and type **UPDATE**.
2. In the authenticated LAN Activity Manager open **Moltbook → Friend Scout**. Ensure global friend scouting is enabled and select an **active watched** friend. Expand **Inspect public activity**, enter `INSPECT PUBLIC ACTIVITY`, click to fetch and refresh. This performs **one** bounded public inspection, not a new periodic job.
3. Under **Manual public focus**, verify the cached API-reported profile and at most two matched public posts. If Ollama returned a tentative reaction, verify reason/uncertainty and approve, reject or reopen locally; if none appears, the profile snapshot still counts as a successful inspection.
4. Try a repeat: cooldown should block it. Pause watching that friend or disable global Friend Scout; inspection must be unavailable. Existing FM3.2c interest inbox and all publication restrictions should remain intact.

**Operational watch item:** Successful dashboard testing is not evidence of a completed scheduled Scout iteration; separately inspect Overview/Scout checkpoint/Logs after an ordinary timer-run if still unconfirmed.

## Roadmap pause

FM3 is complete once this release passes operator acceptance. **Do not start FM4 or FM5** until the operator's reported issues and requested intervening feature have been collected, prioritized and addressed. The separate Activity Manager ↔ Bob agent chat idea remains in TODO.md, not silently merged into FM3.
