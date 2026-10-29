# v0.7.2 publication accuracy and original-draft formatting correction

**Current status (operator-reported October 28, 2026):** The guarded publication-accuracy and original-draft-format update **installed successfully** on OpenClawLab. Installation and focused tests passed; a fresh original-thought request and public-visibility audit remain necessary to demonstrate behavior on real data. Historical published-without-ID records are only relabeled in the dashboard, not rewritten. No automatic retry was enabled.

## Root causes confirmed in source

1. The publisher accepted a successful verification response even without a confirmed comment ID and set `publish_jobs.state='published'`. This does **not** prove a publicly visible comment. New missing-ID outcomes now use `verified_unconfirmed`; any previously returned comment ID is retained after verification. No automatic re-post or retry occurs.
2. Disabling automatic comment publishing in Activity Manager explicitly changes still-`queued` auto jobs to `cancelled`. Those were not submitted and should not be displayed as API failures.
3. Original-draft generation accepted only `TITLE:` plus `BODY_START` markers. Models can generate plausible content in other explicit formats. A bounded parser now accepts labelled TITLE/BODY, exact JSON title/body, or a Markdown heading and body. Every result still passes the existing title/body/community validation, enters the draft queue only, and requires the owner's separate approval to publish. Arbitrary free-form text is still rejected.

## User-facing presentation

The Activity page displays historical `published` comments with no ID as **ID unconfirmed; visibility unknown** without rewriting old database rows. A `published` comment *with* an ID is labelled **API acknowledged; visibility unchecked** until public visibility is independently observed. Publicly confirmed original posts retain their separately verified badge. Canceled auto jobs say **Cancelled before sending**. The summary count distinguishes API-acknowledged comments with IDs from comments whose IDs are unconfirmed. System Status similarly maps historical `published` without ID to a visible `verified_unconfirmed` label.

A comment ID alone is not a public visibility guarantee. Third-party reports in October 2026 describe Moltbook challenge verification succeeding while comments remain absent from public listings. Do not infer that Bob definitely posted, deleted, or was moderated without a read-only public check.

## One bounded public audit, no publishing

From an interactive OpenClawLab shell, after updating the GitHub checkout:

```bash
python3 scripts/audit_comment_visibility.py
```

The audit reads only five recent acknowledged comment jobs from SQLite using `mode=ro`, fetches at most three pages of each public Moltbook comment tree over HTTPS, and reports exact-comment-ID observations without API credentials or POST requests. Results:

- `visible_in_public_listing`: exact ID appeared on a fetched public comment tree.
- `not_observed_in_public_listing`: complete listing returned without that ID; not evidence of deletion.
- `scan_incomplete`: pagination was incomplete, so visibility is unknown.
- `id_unconfirmed`: local job has no validated ID to look for.
- `public_check_unavailable`: HTTP/error/invalid schema; visibility unknown.

Audit does not mutate SQLite or issue retries. Do not paste private job text or credentials to chat.

## Guarded rollout

`scripts/patch_v072_publication_fixes.py` is the explicit-confirmation, version-pinned installer. It compares the exact expected installed manager, publisher, original worker, and status module against pinned pre-fix versions under `release_baselines/v072-pubfix/`. It creates and restore-verifies a fresh private SQLite backup, journals original code, updates only four code files, restarts only the Activity Manager, verifies authenticated HTTP (Settings, Activity, Status/API), and rolls back code if required. Existing running one-shot publisher/original worker processes are not interrupted. Database schema, auto mode, rates, and authorization are unchanged.

Read-only readiness: `python3 scripts/patch_v072_publication_fixes.py`.

Install mode (separate explicit operator approval required): `python3 scripts/patch_v072_publication_fixes.py --apply --confirm UPGRADE-BOB-PUBLICATION-FIX`. An interrupted transaction can use `--recover --confirm RECOVER-BOB-PUBLICATION-FIX` after private-journal inspection. Never rerun a refused/incomplete upgrade blindly.

This is an incremental correction, not a general-purpose release manager or a guarantee that Moltbook displays every API-acknowledged comment.
