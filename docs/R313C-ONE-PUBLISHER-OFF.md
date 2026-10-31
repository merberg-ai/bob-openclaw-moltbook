# R3.13c: source-only single-publisher Bob-comment candidate

**Status: engineering source candidate, not installable, no new Moltbook rights.**
The current installed credentialed v0.7 publisher and `v0.8.0-shadow4` release
manifest remain untouched. No database migration, owner-control UI, credential
read, real GET or POST, systemd service or new publisher is installed or
activated. Both `R312_REAL_DISPATCH=False` and
`R313C_REAL_DISPATCH=False` must be separately reviewed and replaced as part
of a future owner-authorized versioned release. No setting, environment
variable, model decision or CLI flag turns them on.

## Discovered provenance gap: durable Bob action envelope

R3.5-compatible `r3_proposals` stores the independent Bob comment text, seal,
fingerprint and original Scout snapshot hash, but **not the Bob reason** from
his validated original decision. R3.11/R3.12 tests used a marked disposable
`r311-inert-action.json` descriptor. An installed publisher MUST NOT infer
the missing reason from a hash or import that temporary test file.

R3.13c introduces a separately versioned additive production contract:

- `r313c_action_envelopes` keyed by `source_run`: bounded canonical
  `action_json` containing exactly type, source_run, target_id, reason and
  text, plus its SHA256 digest and existing independent Bob seal.
- `r313c_schema_meta.version=r313c-action-v1` to prevent treating a partial
  schema as a validated production install.
- The publisher reconstructs an Action **from the stored immutable envelope**,
  not a caller-supplied model action. It recomputes the saved Scout selection,
  action fingerprint and seal and checks exact envelope-to-proposal-to-queue
  correspondence before admission, at atomic claim and after intent.

The future owner-approved production migration must create these two additive
tables while preserving all legacy and R3.5 data, and must populate envelopes
only through a separately reviewed authenticated proposal producer. This
phase does NOT modify the R3.13b production DB or install such a writer. Old
R3 proposals with no exact envelope remain held, not guessed into existence.

## Actual existing-publisher integration

`src/bin/bob-moltbook-publisher.publisher_step()` now calls the tiny
`bob_r313c_adapter.maybe_r3_publisher_step()` after the original Scout
auto-candidate housekeeping and commit. Its first action is a hardcoded
source-level Off check, which returns `None` without reading R3 schema or
calling HTTP/credentials. The old v0.7 Scout selection and POST path therefore
remains the same as R3.12.

The prospective branch, in `src/bob_v08/r313c_candidate.py`, is bound to
the same `publish_jobs` attempted-at ledger and manual-first whole queue.
It uses the pinned HTTPS GET client (`www.moltbook.com`, exact UUID,
expected author, no bearer/cookies/redirects, six-second timeout and 64-KiB
cap) already created in R3.9, and performs two saved-source/consent reviews
around GET. It additionally checks **new R3.13b manual-enabled consent** and
exact per-Bob-draft approval or separate post-opt-in R3 automatic permission,
in addition to legacy caps/spacing and friend protection.

Under `BEGIN IMMEDIATE`, the same existing queue's exact sealed job is
moved from `queued` to `sending` with `attempted_at` and the linked R3
proposal to `intent`, with one audit event. The transaction is atomic and
manual priority, source integrity, owner consent, friend and budget are
rechecked. **After commit, just before the eventual single credentialed
POST**, it rereads owner controls, source/envelope, proposal, pause marker,
friends and attempted-history/budgets. If any changed, the counted attempt is
locked as uncertain rather than replayed. Concurrent claims, crashes and
unknown responses cannot produce a fresh queued send.

The prospective registered sender would call the existing publisher's
`api("POST", "/posts/<uuid>/comments", {"content": text}, key=api_key())`,
never a second credential store or a model-defined URL. Responses are handled
conservatively:

- API ACK with valid comment ID records the existing queue `published`
  state with an explicit `api_ack_comment_id_not_publicly_reverified`
  audit marker. API acknowledgment is **not independent public verification**.
- Valid verification challenges are held for the existing manual verifier,
  never automatically solved.
- Timeout, malformed/rejected response, post-intent boundary change or
  crashed send becomes `uncertain` and cannot be automatically retried.
  Recovery marks persisted `sending` R3 jobs uncertain without sending.

The candidate's published/verification settlement state follows the same
legacy queue statuses; R3.13d must separately review recovery/visibility UI
semantics and installed verification protocol behavior.

## Testing and deployment gates

`tests/test_r313c_publisher_candidate.py` exercises the actual publisher
executable's default Off behavior and the prospective single-ledger function
against an explicitly marked R3.3 private fixture, an independently sealed
durable action envelope, mock GET, and fake in-memory POST. It includes
envelope tampering, consent revocation, post-claim pause/friend/owner changes,
unknown receipts, human challenge, crashes, recovery, manual-first priority,
duplicate history and competing writers. CI never reads Moltbook tokens or
makes a real external request. Source-level permission review and simulated
success do not authorize actual send.

**Still required before production R3.13d cutover**:

1. Owner-approved versioned additive migration including new envelope tables,
   private verified backup, service drain, rollback and mixed-version safety.
2. Authenticated dashboard owner R3 manual/auto controls and exact Bob draft
   approvals with independent Off defaults; real sealed action producer.
3. Operator-reviewed publisher executable/source/root and installed unit
   attestation, one credentialed sender, full post-verification handling.
4. Explicitly owner-authorized canary, natural scheduled lifecycle and
   Windows/WSL reboot/no-duplicate/code-only rollback.
5. R2 G1 natural timer-driven fresh source-linked decision, still independent.

**R3 cutover authorized: NO.** Leave `releases/current.json` unchanged.
Do not use `bobctl update` to install this source-only candidate.
