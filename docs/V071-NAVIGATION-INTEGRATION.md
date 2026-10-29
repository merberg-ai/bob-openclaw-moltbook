# v0.7.1: Integrated responsive Activity Manager navigation

Status: **integrated, uninstalled development candidate**. The existing 127.0.0.1/LAN dashboard and workers remain on their known-good host versions.

## What changed

The existing Activity Manager already serves three pages: `/` (Scout & review), `/activity` (Published activity), and `/originals` (Original posts). The responsive UI adds desktop sidebar navigation and a CSS-only mobile disclosure menu with accessible navigation landmarks, keyboard focus, active-page indication, and no JavaScript.

`webui/navigation_shell.py` can now safely adapt the server's **original trusted full-page HTML** rather than recreating drafts, forms or database-driven content. It recognizes exactly two pinned legacy navigation shapes, replaces the outer layout, and refuses unknown HTML structures. It does not parse or change user-generated content, POST forms, approval hashes, CSRF tokens, Basic auth, Origin validation or the publishing queue.

`scripts/build_v071_manager_candidate.py` deterministically builds a two-file candidate archive from the SHA-256-pinned reviewed `src/bin/bob-activity-manager`. Exactly three GET response calls are wrapped; the original manager source stays byte-for-byte untouched. The second candidate file is `navigation_shell.py`, which must be alongside the generated manager executable in any future staged release. The archive includes a review manifest and is explicitly non-deployable.

## CI verification

GitHub Actions runs **128 offline tests**, including actual loopback HTTP page rendering, the integrated UI candidate builder, and the existing source-rollback, inert service-graph, static systemd parser and process-lifecycle simulations. New tests verify route allowlisting, HTML escaping, exact form and hidden token preservation, the unchanged AST of *every* non-GET request-handler method, and the generated candidate's three actual GET handler paths under synthetic HOME.

## Development-only acceptance

From the v0.7.1 feature checkout, running `python3 scripts/build_v071_manager_candidate.py` performs checks without writing or installing anything. With `--private-review-zip`, it creates a mode-0600 ZIP under the operator's private `~/.local/state/bob-baseline/v071-candidates/` directory; this is a review input, **not** a deployment command. No new code runs against the live database or API.

## Next integration gates

1. **Completed in CI:** Generated candidate ran under a fresh synthetic HOME and SQLite database using an ephemeral `127.0.0.1` HTTP listener. All three actual GET pages and `/healthz` responded 200, existing Content-Security-Policy remained intact, and requests with an unexpected Host were rejected 403. The test made no POST or external API calls.
2. Responsive CSS refinement is implemented: mobile disclosure fix, keyboard skip-link, touch targets, and narrow-screen form sizing. Browser pixel/visual acceptance is still pending.
3. A checksummed, two-file review package and isolated atomic code-switch/rollback rehearsal are complete. A production installer and live-host permission remain separate, pending gates. See [UI update rehearsal](V071-UI-UPDATE-REHEARSAL.md).

No live service reload, restart, Windows Task Scheduler change, Moltbook request or database migration occurred during this phase.
