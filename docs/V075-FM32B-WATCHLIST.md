# FM3.2b: paginated Friend Scout watchlist and evidence-linked recency

**Candidate:** `v0.7.5-fm32b-watchlist1`, from operator-confirmed `v0.7.5-fm32a-interests1`.

## Changes

On the existing authenticated **Moltbook → Friend Scout** page:

- **Pagination:** all integrity-verified *active* FM1 friends can be reached in stable, ten-agent pages (up to the existing 300-record FM1 cap), rather than showing only the first ten.
- **Filter:** search by agent handle or display label; select **All active**, **Watched**, **Paused**, or **Integrity issues**. Private friend notes/interests are never searched or echoed. An invalid/out-of-range page is bounded; filter parameters are treated as view state only.
- **Return after watch change:** individual watch-toggle forms carry the canonical page/filter in the action URL (no additional POST fields). After existing Basic authentication, Origin and CSRF checks and a successful digest-guarded change, the Activity Manager redirects only to a whitelist-built same-origin Friend Scout URL, retaining the operator's filtered page.
- **Evidence-linked Scout recency:** a source-checked saved friend-focused post is labeled **Last verified friend-focused source**. A chosen author/post verified against the saved Scout feed is labeled **Last selected discussion**, including selections from the global feed. Both display the saved Scout run's UTC timestamp and run ID. These are local historical *observations*, not online-presence timestamps, a social exchange, account identity verification or proof of mutual friendship. If no suitable verified source exists among the **100 most recent saved Scout records**, the page states so rather than inventing dates.

All evidence lookups require independently validated saved Scout results, the exact associated feed checksum, valid post UUID and author matched to an integrity-checked active FM1 entry. Missing or altered sources provide **no activity timestamp**. No HTTP or model call is performed to display this information.

## Deployment and security

Two managed files change: `bob_friend_scout.py` and the generated `bob-activity-manager`. A new release builder derives from the previous `build_v075_logs_candidate.py` and performs exactly three pinned substitutions (module import, bounded GET query handoff, canonical post-update redirect). The navigation shell and previous dashboard auth, CSRF, publication handlers, and worker code remain byte-identical. The existing updater's verified backups and guarded rollback remain in force; the dashboard is the only requested restart. No new module installations are required.

Unchanged boundaries: global friend Scout default-off, individual watch pause, only two active watched friends inspected per Scout iteration, one public post each, at least four global posts, never automatic friend-targeted comments, manual review for outbound replies, no new schedule/network permissions/follows/DMs. FM3.2a interest reviews remain local-only.

## Offline acceptance

The synthetic tests cover 25 verified friends across three pages; watched/paused/issue filters; case-insensitive search; invalid parameters and escaped HTML; preserving the canonical view across a watch POST; independently verified last focused/last chosen reports, global selected-source distinction, absent/tampered evidence, and the *exact dashboard change set*. Full repository CI must pass before merging.

## Short operator acceptance

1. On OpenClawLab run **`bobctl update`** once; verify `v0.7.5-fm32a-interests1` → `v0.7.5-fm32b-watchlist1`, two files, then type **UPDATE**.
2. In the authenticated LAN Activity Manager open **Moltbook → Friend Scout**. Search for an agent and filter by **Watched** or **Paused**. Toggle one friend's watch; verify the view stays filtered and the stored setting changes. With more than ten active agents, use **Next page**.
3. If any verified saved friend-focused or selected discussions exist among recent Scout records, their UTC date/run appears in the card. If not, the empty-state label is correct. Neither page load nor filtering contacts Moltbook.
4. Check that existing **Tentative interests** and prior manual publication behavior still work. No additional live commands are necessary.

## Follow-up

FM3.2c can add new bounded local-model interest suggestions only after separate source validation and owner review, including explicit uncertainty and provenance. The optional manually confirmed one-friend public read is a further opt-in design item; FM4 and FM5 remain separate later phases.
