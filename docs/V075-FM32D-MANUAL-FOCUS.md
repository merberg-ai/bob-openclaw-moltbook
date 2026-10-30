# FM3.2d: opt-in, verified public focus for a watched friend

**Release:** `v0.7.5-fm32d-focus1`, upgrading from operator-confirmed `v0.7.5-fm32c-localideas1`. **Status: OPERATOR ACCEPTANCE PASSED, October 30, 2026.** This closes the planned FM3 work. FM4 and FM5 remain **on hold** until the operator's other issues and requested intervening feature are addressed.

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

**Result: PASSED.** PR [#38](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/38) was merged into `main` (commit `8c710239178097e08e801d1ab064097bbb6154f0`); GitHub Actions completed **537 offline tests successfully**. After normal `bobctl update`, the operator reported on **October 30, 2026** that the release "seems to be working as expected" and specifically requested marking it passed.

This is an operator acceptance of the installed dashboard feature, not independent remote inspection of host binaries or the next timer-triggered Scout run.

### Historical live acceptance checklist (completed by operator at smoke-test level)

After offline CI passes and the PR is merged:
1. In OpenClawLab run **`bobctl update`**. Confirm `v0.7.5-fm32c-localideas1` → `v0.7.5-fm32d-focus1`, review two-file proposal and type **UPDATE**.
2. In the authenticated LAN Activity Manager open **Moltbook → Friend Scout**. Ensure global friend scouting is enabled and select an **active watched** friend. Expand **Inspect public activity**, enter `INSPECT PUBLIC ACTIVITY`, click to fetch and refresh. This performs **one** bounded public inspection, not a new periodic job.
3. Under **Manual public focus**, verify the cached API-reported profile and at most two matched public posts. If Ollama returned a tentative reaction, verify reason/uncertainty and approve, reject or reopen locally; if none appears, the profile snapshot still counts as a successful inspection.
4. Try a repeat: cooldown should block it. Pause watching that friend or disable global Friend Scout; inspection must be unavailable. Existing FM3.2c interest inbox and all publication restrictions should remain intact.

**Operational watch item:** Successful dashboard testing is not evidence of a completed scheduled Scout iteration; separately inspect Overview/Scout checkpoint/Logs after an ordinary timer-run if still unconfirmed.

## Roadmap pause

**FM3 is COMPLETE and accepted.** **Do not start FM4 or FM5** until the operator's reported issues and requested intervening feature have been discussed, prioritized and addressed, and the operator expressly agrees to resume Friends work. The next Friends engineering step is **FM4.1: evidence-linked private Social Memory Timeline**. Detailed scoping, source boundaries, release-baseline rules and a copyable fresh-chat kickoff are recorded in [FRIENDS-ROADMAP-AND-HANDOFF.md](FRIENDS-ROADMAP-AND-HANDOFF.md).

The separate Activity Manager ↔ Bob agent chat plan remains in root [TODO.md](../TODO.md), not assumed to be the requested new feature. This documentation acceptance change **does not modify `releases/current.json`, issue a new version, or require another `bobctl update`**.
