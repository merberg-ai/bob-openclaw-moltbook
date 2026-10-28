# v0.7.1: Integrated responsive Activity Manager navigation

Status: **integrated, uninstalled development candidate**. The existing 127.0.0.1/LAN dashboard and workers remain on their known-good host versions.

## What changed

The existing Activity Manager already serves three pages: `/` (Scout & review), `/activity` (Published activity), and `/originals` (Original posts). The responsive UI adds desktop sidebar navigation and a CSS-only mobile disclosure menu with accessible navigation landmarks, keyboard focus, active-page indication, and no JavaScript.

`webui/navigation_shell.py` can now safely adapt the server's **original trusted full-page HTML** rather than recreating drafts, forms or database-driven content. It recognizes exactly two pinned legacy navigation shapes, replaces the outer layout, and refuses unknown HTML structures. It does not parse or change user-generated content, POST forms, approval hashes, CSRF tokens, Basic auth, Origin validation or the publishing queue.

`scripts/build_v071_manager_candidate.py` deterministically builds a two-file candidate archive from the SHA-256-pinned reviewed `src/bin/bob-activity-manager`. Exactly three GET response calls are wrapped; the original manager source stays byte-for-byte untouched. The second candidate file is `navigation_shell.py`, which must be alongside the generated manager executable in any future staged release. The archive includes a review manifest and is explicitly non-deployable.

## CI verification

GitHub Actions runs the full baseline offline suite, the integrated UI candidate builder, and the existing source-rollback, inert service-graph, static systemd parser and process-lifecycle simulations. New tests verify route allowlisting, HTML escaping, exact form and hidden token preservation, the unchanged AST of *every* non-GET request-handler method, and the generated candidate's three actual GET handler paths under synthetic HOME.

## Development-only acceptance

From the v0.7.1 feature checkout, running `python3 scripts/build_v071_manager_candidate.py` performs checks without writing or installing anything. With `--private-review-zip`, it creates a mode-0600 ZIP under the operator's private `~/.local/state/bob-baseline/v071-candidates/` directory; this is a review input, **not** a deployment command. No new code runs against the live database or API.

## Next integration gates

1. Run the generated candidate against a synthetic database in a separately bound loopback-only HTTP test harness, verifying real rendered markup and route response codes, with no Moltbook publishing or external model access.
2. Verify the actual mobile/browser layout and form usability; correct CSS behavior without changing business logic or introducing JavaScript into authenticated forms.
3. Build a verified staged release package with explicit original-source compatibility and rollback, then request the operator's permission for a controlled service update. The existing WSL startup and live database must remain intact.

No live service reload, restart, Windows Task Scheduler change, Moltbook request or database migration occurred during this phase.
