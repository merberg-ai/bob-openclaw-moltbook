# Consolidated v0.8 R3 cutover: G2 receipts and one guarded release

**Status:** source and acceptance plan. The installed v0.8.0-chhttps3 release is unchanged.
**Safety:** R3 real Moltbook publishing remains hard Off. No owner cutover or canary authorization follows from this plan.

## Accepted production baseline

R1 updater and R2 Shadow4 have been accepted. The R2 timer has run, although a naturally scheduled **source-linked decision** remains a distinct outstanding G1 observation; do not force replay for it.

R3.13d additive Off-only schema/journal is installed and preserves 23 attempted legacy jobs and 0 uncertain, both before and after Windows reboot. The Activity Manager is HTTPS only; OpenClawLab, Gateway, manager and original timers recovered successfully at Windows interactive login. The WSL Hyper-V firewall is enabled/default Block with an allow rule for TCP 18790 from 192.168.1.0/24. The owner reports no outside reachability. These are good operational observations, not a comprehensive independent WAN scan.

## G2 reconciliation: ONE bounded owner command

The source-only `scripts/report_g2_public_receipts.py` uses the existing `audit_comment_visibility.py` anonymous public HTTPS GET checker on the fixed Moltbook endpoint, with no credentials. It reads the private `publish_jobs` table with SQLite `mode=ro` and `PRAGMA query_only`. It audits at most 40 historically attempted legacy comment jobs, and checks at most two bounded public listing pages per valid saved receipt. No source text, passwords, comments, or private IDs are printed. It performs no POST, database writes, systemd changes or R3 permission changes.

After reviewed CI/merge, run from the normal OpenClawLab `openclaw` shell:

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/report_g2_public_receipts.py --public-get
```

The flag explicitly permits **anonymous public GETs only**. Without it, the script is local-only. Optional `--json` prints aggregate counters, not content. It compares local snapshots around the network checks and marks a moving database or truncated history incomplete.

- `status: known_receipts_visible` means every attempted comment in this bounded scope had a saved comment ID visible in its public thread, and there were no local duplicate-target/receipt or unknown/uncertain-state flags. It **does not** prove there are no additional unrecorded external posts.
- `status: review_required` is an honest completed audit with missing receipts, failed/unavailable public lookups, incomplete pagination, repeated attempted targets (possibly legitimate), unfamiliar queue states, or moving/truncated history. It does **not** authorize replays or repeated forced publisher runs.
- `external_duplicate_posting_excluded` is always false. Public listings can omit entries; an extra unrecorded reply would not be ruled out by matching a known ID. Original posts are outside this comment audit.

If the audit returns unresolved rows, review only the flagged categories and actual remote receipts/source records. Never replay attempted or uncertain jobs, restore a stale SQLite backup, or change the publisher to make an audit pass.

## R3 cutover1: ONE integrated engineering and deployment batch

Build one versioned `v0.8.0-cutover1` candidate whose upgrade chain starts from the **actually installed `v0.8.0-chhttps3`**. Package all the following together:

1. A single source-sealed real-OpenClaw-Bob proposal/decision loop, with strict target/text identity and no new runtime Moltbook credentials. R2 Shadow remains unchanged until a reviewed service handoff.
2. Exactly **one external writer**: extend the existing credentialed legacy publisher hook in the same `publish_jobs` queue. No separate R3 HTTP publisher or second dispatch timer. Preserve manual approvals and legacy original-post flow.
3. Atomic intent-before-POST and final source/author, consent, friend-policy, pause, budget, manual-first priority and duplicate/unknown-history checks. Treat API acknowledgement, verified public comment, failed and uncertain states distinctly. Never auto-retry uncertain sends.
4. One owner-visible R3 Controls/Now/Inbox authority, with default-Off new automatic Bob actions. Managed, exact-name transition of any conflicting old decision timer; never disable existing publisher/Scout prematurely or silently enlarge permissions.
5. Additive schema/backward-compatibility and **code-and-unit-only rollback**, preserving historical and newly attempted posts. Never restore an earlier SQLite snapshot after any possible send.
6. Offline isolated CI for concurrency, crash/pause/rollback, rate/friend restrictions, duplicate cases, queue ordering, and source tampering. No external Moltbook writes during CI.

### One owner acceptance, not dozens of micro-tests

**Engineering:** implement in integrated batches on `next`, run all synthetic tests and isolated recovery rehearsal in CI, and review the exact candidate manifest. Do not promote or install an unfinished candidate.

**One release acceptance:** after explicit owner approval, `bobctl update --check`, one `bobctl update`, and **one consolidated installed health/permission report** with the new publisher still default Off. Do not require the owner to test each PR separately.

**Separate optional public canary:** only after the owner separately approves one exact source/post, draft and send attempt. Verify public receipt rather than treating API ACK as published. Auto-R3 remains Off until its own explicit opt-in. On failure, keep Off, preserve the ledger, and use code/unit-only rollback.

## After R3

R4 is one integrated social-autonomy and UI release: verified Moltbook follow/upvote/unfollow APIs if supported, independent exploration, evidence-grounded relationships/digests, consolidated Now/Inbox/Bob/Controls and robust anomaly pause, all opt-in. CH1 real OpenClaw LAN Chat is a later separate feature, not a hidden R3 prerequisite.

**Operator time budget:** one useful G2 read-only report, one consolidated R3 release acceptance, and an optional exact canary. No new chains of installer commands for trivial UI patches.
