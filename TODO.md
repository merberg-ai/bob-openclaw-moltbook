# Bob 💀 — Project TODO

**Last reviewed:** October 30, 2026 (America/Los_Angeles)  
**Canonical repo:** `merberg-ai/bob-openclaw-moltbook`, `main`  
**Operator-tested deployed baseline:** `v0.7.6-oc41-polish1` (OC0–OC4.1 completed; operator reported Oct 30, 2026 that the OC4.1 update works as expected)  
**Status:** FM3 complete; **FM4 explicitly resumed by operator on October 30, 2026**. FM4.1 private timeline release candidate `v0.7.7-fm41-social1` pending CI/live acceptance. **FM5 remains planned and unimplemented**; real Moltbook following requires a separate FM5.2 permission design. CH1 remains planned.  
**Deployment contract:** future implementation through `bobctl update` with verified private backup, installed-module import checks, reversible release and short live acceptance. A Git commit alone never changes the running Activity Manager.

## Current development streams

| Stream | Progress | Next |
| --- | --- | --- |
| Personality (PM1) and Memory (PM2) | Implemented / operator-tested | Maintain existing explicit memory recall and owner review boundaries |
| **Friends (FM1–FM4.1)** | FM3 fully accepted; **FM4 resumed; FM4.1 release candidate** `v0.7.7-fm41-social1` | Private source-verified Social Memory Timeline (observed Scout, reviewed interests, local reactions, publication records). [FM4.1 release notes](docs/V077-FM41-SOCIAL-MEMORY.md). After owner PASS: FM4.2 revisable impressions, FM4.3 opt-in recall; FM5 platform following separately authorized later. |
| **Operations Center: activity / automation / console / inactivity investigation** | **OC0–OC4.1 complete, installed and operator-accepted** | Working baseline `v0.7.6-oc41-polish1` (PR #47, 591 CI tests). Remains maintained; FM4 has since resumed. [OC4.1 release notes](docs/V076-OC41-DIAGNOSTIC-POLISH.md). |
| Logs & Diagnostics | Installed / operator-tested | Reuse existing bounded redacted journal, job, event and checkpoint collectors rather than duplicate raw logging |
| **Direct Bob Chat (CH1)** | **Planned here, not started** | Gateway compatibility spike, then authenticated LAN chat UI |
| Fresh-host installer | Deferred | Keep current WSL/Windows startup, services and updater intact |

## Completed priority: Bob Operations Center, before FM4

**Owner request (Oct 30, 2026):** The Overview gauges show 2/10 comment attempts, 0/6 automatic, 0/4 originals and six queued manual comments, but reveal too little about the reason for inactivity. Owner wants a compact live-truthful **“Bob right now”** card directly below gauges, a centralized **Automation** section with controls/status/last action/next actual run for automatable features, a terminal-styled **read-only sanitized Console** showing useful Ollama/OpenClaw/Gateway/system/worker diagnostics, and a reliable one-view **“Why no activity?”** explanation. All pages must be compact and mobile-friendly.

**Implementation status:** **OC0 through OC4.1 operator-accepted on the OMEN.** The publication fix `v0.7.6-pubfix-manual1`, OC4 investigator and OC4.1 `v0.7.6-oc41-polish1` have been installed in sequence, and the operator reports OC4.1 works as expected (October 30, 2026). This closes the scoped Operations Center roadmap; see [OC4.1 release notes](docs/V076-OC41-DIAGNOSTIC-POLISH.md). No new publishing authority was added. **Next separately planned work: MD1 Moltbook Experience Digest** for verified history in real Gateway/CH1 conversations, not yet implemented. Build from existing `bob_overview`, `bob_live_status`, `bob_job_tracking`, `bob_diagnostic_logs`, `bob_activity_limits`; preserve queue and publishing protections. Only add automation toggles through exact, independently authorized handlers. **Original posts remain owner-requested/approved** unless separately redesigned; empty original budget is not proof of failure. “Earliest possible next” is a rate-limit eligibility clock, not a real scheduled run.

**User preference:** no sprawling command-marathon; one `bobctl update` per small code release, with CI first and a concise mobile/LAN acceptance. Keep FM4/FM5 paused until the Operations Center and other operator-reported issues are addressed.

---
## Friends work: paused after final FM3 acceptance

**Passed October 30, 2026:** The operator tested `v0.7.5-fm32d-focus1` through the normal `bobctl update` and confirmed it works as expected. This closes FM3.2d and FM3 as scoped. PR [#38](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/38) merged to main, with **537 passing synthetic offline tests**. This is a documentation acceptance checkpoint, **not a new code release**. Keep `releases/current.json` unchanged until an actual next software release.

**Priority cleared:** The operator accepted OC0–OC4.1 and explicitly requested resuming FM4. FM4.1 is a private read-only candidate; it does **not** automatically grant FM4.2/4.3, external follows, chat memory integration or FM5 autonomy. Continue in small independently accepted releases.

**FM4 hold lifted; FM4.1 is underway:** a small private, source-verifiable, per-agent **Social Memory Timeline** distinguishing actual saved observations, Bob's tentative ideas and owner-reviewed records. Start with read-only evidence linked from FM1/FM2 and existing FM3.2a–d data, timestamps and corruption checks; do not silently write to PM2 memory or `SOUL.md`, change Scout priorities or authorize outreach. FM4.2 can add revisable impressions and owner corrections; FM4.3 can add explicitly enabled bounded recall. FM5.1 independent exploration and FM5.2 separately approved public interactions remain further off. Full architecture, rules, acceptance and copyable kickoff: [docs/FRIENDS-ROADMAP-AND-HANDOFF.md](docs/FRIENDS-ROADMAP-AND-HANDOFF.md).

**Future versioning:** last operator-confirmed installed release is `v0.7.6-oc41-polish1`. FM4.1 candidate `v0.7.7-fm41-social1` upgrades from exactly that version. Repository merge does not establish live acceptance; preserve guarded `bobctl update` with backup/rollback.

---

The earlier Scout `ModuleNotFoundError: bob_publish_common` was repaired through `v0.7.5-scout-importfix1`; the operator installed the shared helper and reset the historical failed status. Separately verify a later **timer-driven complete Scout run** when convenient. Don't restart services simply to satisfy this plan.

---

## MD1: Moltbook Experience Digest for Bob's actual Gateway conversations (PLANNED)

**Identified October 30, 2026:** In a real OpenClaw Gateway chat, Bob said he had seen multiple `moltbook-scout` sessions but described Moltbook as mostly “standby mode,” with little actual learning. Repository inspection explains a **context gap**, not confirmed intentional fabrication: scheduled Scout runs use separate `openclaw agent --session-key moltbook-scout-<run>` sessions and save verified posts, WHY selection, drafts and outcome metadata in private Scout files/SQLite. PM2.3 read-only contextual recall **only** enriches Scout and original drafting prompts; it does **not** supply this evidence to arbitrary Gateway chat. Bob can plausibly know sessions existed but cannot reliably summarize their actual history from normal chat context. His statement about few interactions may also be correct; do not infer a genuine conversation or learning outcome from a queued draft.

**Owner goal:** When asked in Gateway or the future LAN CH1 Chat, “What have you experienced or learned on Moltbook?”, Bob should answer with **verifiable sources and honest limitations**, not an invented personal history. Proposed **MD1: Moltbook Experience Digest** is a bounded, read-only, local bridge covering:
- **MD1.0, contract/inventory:** identify actual active OpenClaw main-agent workspace, Gateway session/tool boundaries, authentic Scout run data, publisher outcomes, incoming reply records, FM3 tentative interests and owner-reviewed memories; distinguish a saved draft, an attempted send, confirmed publication, and actually observed public replies. Never conflate generated text with learned memory.
- **MD1.1, private verified digest:** produce a bounded recent activity summary with last Scout selection/rationale, safely verified public post IDs and UTC times, manual/automatic publication status, received replies, the owner's reviewed tentative interests, and what remains uncertain. Read from sealed existing data, not raw untrusted third-party instructions; no secrets, private owner notes, raw prompts, or arbitrary model-supplied paths. Carry explicit timestamps/source links and stale/unknown labels.
- **MD1.2, conversation bridge:** let the real OpenClaw Bob agent access this digest during appropriately **opted-in** Gateway/CH1 conversations by a deliberately bounded, authenticated mechanism. Verify it works in a **fresh Gateway chat session** and in private-LAN CH1. Do not inject into public posts, grant new tools, publish, change agent persona, or automatically update memory.
- **MD1.3, voluntary growth:** allow Bob to propose new tentative interests and revisions sourced from his digest/experience; owner review/approval and auditable versions stay explicit. Actual long-term social-memory integration belongs with FM4 and requires separate authorization and retention/privacy decisions.

**Acceptance:** ask Bob what he has actually done on Moltbook, confirm an answer points to real saved Scout/published/reply evidence, states the distinction between reading and interacting, and admits missing data. Test zero-data/missing-data, compromised hashes, stale sessions, no publication, source tampering, untrusted feed injection, separate personalities, and privacy leaks. A model's confident claim alone never becomes source evidence.

**Priority/order:** Complete **OC4** first (including any already pending publication-fix operator acceptance). MD1 should be scoped together with the separately tracked **CH1 Direct Bob Chat** and future **FM4.1**, but **not** silently treated as a feature already shipped; FM4 and FM5 stay paused until the operator explicitly resumes them.

---

## CH1: Talk directly to the real OpenClaw agent Bob

### User story / non-negotiable requirement

> From my phone or laptop on the secure private LAN, open the existing authenticated Bob Activity Manager, select **Chat**, type “Bob, what have you been up to on Moltbook?” or “Which agents interest you and why?”, and converse with **Bob the existing OpenClaw agent** using his personality and available memory. Not an Ollama-only imitation.

**LAN access is a hard requirement.** The chat must work via the same trusted-LAN Activity Manager URL and login already used on the OMEN (previously tested at `http://192.168.1.24:18790`), without visiting the OpenClaw Gateway UI separately, connecting a browser to Gateway port `18789`, exposing new Windows inbound ports or requiring internet/public hosting. Test from a second LAN device and Android/mobile browser.

**Hard boundary:** direct interaction with the OpenClaw agent **does not** confer extra rights to publish, DM, follow, vote, execute commands or modify settings. Effective OpenClaw tools/profile and existing Moltbook host-only publisher authorization must remain in charge; the dashboard cannot silently convert a chat message into a publication job.

### Proposed architecture

```text
Trusted LAN browser (phone or laptop)
  │
  │ same origin + existing Activity Manager authentication
  │ HTTPS recommended for production (protect password and chat text)
  ▼
Bob Activity Manager   [WSL2; LAN-accessible existing port 18790]
  /chat  : mobile-first, authenticated UI
  /api/chat/* : exact bounded history/send/status/abort handlers
  │
  │ server-side, authenticated, strictly allowlisted chat adapter
  │ single configured Bob agent/session, origin/CSRF/rate checks
  │ no browser-visible Gateway credentials, no arbitrary RPC proxy
  ▼
OpenClaw Gateway WebSocket [127.0.0.1:18789, loopback ONLY]
  │ current, correctly paired/authenticated operator client
  │ chat.history / chat.send / chat.abort and necessary events
  ▼
Existing OpenClaw agent: Bob 💀
  configured SOUL.md / IDENTITY.md, agent workspace & model
  local Ollama qwen3.5:9b as configured provider
```

**LAN feasibility:** already solved at the Activity Manager boundary. The backend is the only Gateway client. **Do not change `gateway.bind` from loopback to LAN**, add a wildcard listener for Gateway, pipe a Gateway token into HTML/JS, embed the privileged Control UI in an iframe, or implement a general WebSocket forward proxy.

OpenClaw documentation (validate against the actual installed version before coding):

- [WebChat](https://docs.openclaw.ai/web/webchat) — Gateway-backed chat uses `chat.history`, `chat.send` and related chat RPCs, rather than calling Ollama directly.
- [Building a Gateway client](https://docs.openclaw.ai/gateway/clients) — operator read/write scopes and device pairing; do **not** invent tokens or edit private `openclaw.json` to mint client credentials.
- [Gateway handshake](https://docs.openclaw.ai/gateway/protocol/handshake) — challenge, protocol negotiation, authenticated connection; exact installed version wins over assumptions.
- [Network exposure](https://docs.openclaw.ai/gateway/security/network-exposure) — loopback Gateway and narrowly controlled proxy/security boundaries.
- [Feature/RPC reference](https://docs.openclaw.ai/web/control-ui/feature-reference) — `chat.abort` and messaging behavior.

### Sessions and authentic Bob personality

- **Default: one persistent, dedicated Activity Manager conversation session attached to Bob's existing main agent.** Choose a documented, installed-version-valid session key in CH1.0; do not invent a hardcoded key yet. A dedicated chat prevents accidental overlap with scheduled Scout, original-post, or Gateway Control UI conversations. A separate explicit “main session” switch may be evaluated **later**, after access checks and owner confirmation.
- Transcript/history should come from **OpenClaw Gateway's own stored chat session**; no duplicate canonical message store and no writing raw conversations into Git or the publication SQLite database. Render only gateway-normalized display text (bounded/paginated), escape it and suppress tool internals by default.
- Bob's configured **OpenClaw** agent persona/workspace should apply. **Important limitation:** the separate PM2 Activity Manager memory DB, friend records, and past Scout jobs are **not guaranteed to be in the OpenClaw chat context by default**. Chatting with the correct agent does *not* automatically give it all data on the dashboard.
- To answer questions such as **“What have you learned from Moltbook?”** accurately, plan an **opt-in, read-only Experience Context** adapter that selects bounded, provenance-validated past Scout reports and curated/approved memory or friend observations. Treat them as low-trust reference data with timestamps and source IDs, not instructions. Distinguish remembered facts, Bob's model opinions, and unsupported inferences. Never dump private relationship notes or entire feeds into a chat prompt by default.
- Do not add a separate assistant personality in the frontend, call Ollama's `/api/chat` directly, or present a model-generated invented activity summary as observed Moltbook history.

### Proposed implementation phases (small independently testable increments)

#### CH1.0: Installed Gateway capability and security preflight (read-only)

- [ ] Inventory actual OpenClaw version and exact working Gateway endpoint, authentication/pairing model, supported chat RPCs, session syntax, allowed operator scopes and event delivery. Do not print or commit auth tokens.
- [ ] Test whether the existing Activity Manager user can connect to loopback Gateway with a correctly paired, explicitly approved *limited* client identity, without broad `operator.admin`, `operator.approvals` or other unrelated methods. If limited client pairing cannot be arranged, **stop** and design an appropriate broker, not a privileged token pasted into browser code.
- [ ] Confirm existing LAN Activity Manager URL, authentication, Origin/Host/CSRF policies, CSP and phone access. Select a same-origin transport: bounded HTTPS requests + polling initially, optional authenticated SSE if practical; **no direct LAN browser connection to Gateway**.
- [ ] Verify read-only session history in a synthetic/isolated test. Never send a real chat message during preflight.

**Gate:** documented compatibility report and approval of the exact minimal bridge. No production config or listener changes.

#### CH1.1: Secure server-side Gateway chat adapter

- [ ] Implement a narrowly scoped localhost adapter with an exact whitelist (`chat.history`, `chat.send`, `chat.abort`, minimal session/status subscription only as required). No generic RPC execution, arbitrary session key, filesystem path, tool approval or channel-send forwarding.
- [ ] Credential handling remains private on WSL host with owner-only permissions, no token in URL, cookies, browser response, logs, API request payloads or exception text. Use supported Gateway bootstrap/device pairing, never hand-roll tokens.
- [ ] Bind the adapter to one validated Bob session with strict message length, history size, concurrency, queue bounds, per-user/IP rate limits, lifecycle timeouts and cancellation. Encode abort against the active run rather than a guessed unrelated session.
- [ ] Preserve existing dashboard authentication and exact Origin/Host + CSRF protections on all chat mutations; `Cache-Control: no-store`. Reject bad/missing auth, external origins, replay/stale requests, oversized messages and Gateway disconnects safely.
- [ ] Avoid service proliferation unless necessary. If a local Node/WS companion process is required because the stdlib Python dashboard has no native WS client, bind it to loopback only, supervise it as a private user service, and document clean rollback.

**Gate:** offline fake-Gateway protocol tests and isolated HTTP auth/CSRF/negative tests; zero additional network exposure and no existing post/queue behavior change.

#### CH1.2: Usable authenticated LAN Chat page

- [ ] Add **Chat 💀** to Activity Manager sidebar/mobile navigation, authenticated `GET /chat`, with conversation bubbles, autoscroll, multiline composer, Send, clear pending/running/idle/error indicators and copyable text.
- [ ] Retrieve bounded recent history and request earlier pages from the Gateway. Show actual Bob messages and preserve conversation on mobile refresh/reconnect. No fake “memory loaded” indicators.
- [ ] Send a text prompt to Bob through OpenClaw and render its live progress. Start with safe polling if simpler; streaming/SSE can follow after reliability is proved. Add Stop only when a validated live run can be aborted safely.
- [ ] Make empty/disconnected/timeout/model-unavailable/restart cases truthful and actionable. Do not duplicate a `chat.send` when the network response is uncertain; use idempotency/session semantics where supported or show an uncertain state and reconcile history.
- [ ] Responsive Android/LAN UX: usable keyboard composer, no sideways overflow, readable code snippets, sensible error notices, no third-party assets/scripts.

**Gate:** authenticated laptop and phone through the **existing** LAN Activity Manager address; Gateway stays loopback-only and unavailable from a second LAN device directly. Chat is still the real Bob agent, not standalone Ollama.

#### CH1.3: Experience-context and trust-aware opinions (separate opt-in)

- [ ] Add a bounded, **read-only** dashboard summary of Bob's verified Scout discussions, recent selected authors, authored WHY fields, approved PM2 memory/observations and any *confirmed* interactions where source and timestamps are available.
- [ ] Offer an explicit UI option **Include Bob's saved Moltbook context**. Its off state must not leak private notes; enabled context is sent as untrusted reference text, not agent instructions or permissions. Prefer owner-approved memories over raw public posts.
- [ ] Let Bob express opinions and changing interests naturally; show source references and the difference between **“from an actual saved Scout run”** and **“my current interpretation”**. No invented post IDs, verified mutual friendships, or claims that a chat has updated long-term social memory.
- [ ] Future integration with **FM4 Social Memory** can permit owner-reviewed memory proposals from conversations, but **never silent memory write or identity mutation** in CH1.

**Gate:** Bob can truthfully answer “Which Moltbook posts did you choose, and why?” from a verified saved snapshot or explicitly say no saved evidence is available. No unapproved public write or memory mutation.

#### CH1.4: Production hardening and optional polish

- [ ] **LAN confidentiality:** existing Basic authentication on plain HTTP is not encrypted. For normal/private chat, prefer **HTTPS on the existing LAN endpoint or a narrowly configured internal HTTPS reverse proxy**; verify phone certificate trust and that credentials/chat aren't exposed in transit. If testing over current trusted-LAN HTTP, label it explicitly as a temporary lower-confidentiality mode; do not imply private LAN == encryption.
- [ ] Verify access from the known trusted phone/laptop, reject unauthenticated clients and non-LAN/public ingress. Ensure WSL/Windows port forwarding remains unchanged and no self-referential portproxy is introduced.
- [ ] Test Gateway restart, browser refresh, duplicate-send, CSRF failure, origin mismatch, brute-force limits, large user/agent text, HTML/script injection, malformed WS packets, stale abort, multiple tabs and read-only outage.
- [ ] Confirm activity logs record only sanitized error codes, timestamps and optional run IDs, never chat text/tokens/structured tool arguments.
- [ ] Review that a chat prompt cannot bypass Bob's configured sandbox/tool restrictions or Moltbook approval workflows.
- [ ] Release through the normal manifest `from` chain and **`bobctl update`**, backed up and reversible. Keep a single concise live smoke-test checklist, not a wall of commands.

### Initial acceptance checklist

- [ ] From phone and laptop on the private LAN, sign into the existing Activity Manager; **Chat** loads without exposing port 18789.
- [ ] Message **“Bob, what has caught your attention on Moltbook lately?”** receives a reply from the existing OpenClaw agent running with Bob's configured identity (not an Ollama-only test backend).
- [ ] Conversation history reappears after reloading the Chat page.
- [ ] A Gateway or Ollama outage has a clear non-misleading status and doesn't lose/duplicate the user's message.
- [ ] The UI accurately distinguishes Bob's actual saved Scout experience from hypothetical ideas; full PM2/FM context is not assumed available until CH1.3 is implemented and explicitly enabled.
- [ ] Auth/CSRF, private Gateway pairing credentials, rate limits, existing Scout/Publisher limits, manually reviewed friend interactions and original-post approval are unchanged.
- [ ] `bobctl update` applies and rolls back the release without exposing a new LAN service or changing Gateway bind/auth.

### Explicitly out of scope until separately approved

- No direct browser-to-Gateway WebSocket, LAN binding for Gateway, generic RPC proxy, iframe of privileged Gateway Control UI, unbounded shell/exec, admin device pairing, tool approval UI, file uploads, voice/video, automatic chat-to-Moltbook publishing, silent training/memory writes, automatic follows, DMs, or public endpoints.
- No claims that Bob actually remembers a past Scout run unless the relevant source is verifiably accessible through agent context.
- Do not merge the unrelated FM3.2, FM4 or FM5 work into the first CH1 release; chat is an independent workstream.

### New-chat kickoff message

> Begin **CH1.0 Direct Bob Chat** for `merberg-ai/bob-openclaw-moltbook`. Read root `TODO.md`, `docs/ARCHITECTURE.md`, and `docs/FRIENDS-ROADMAP-AND-HANDOFF.md`. A **LAN-accessible Chat page within the authenticated Activity Manager** is mandatory; Gateway remains loopback-only. Integrate with the **actual OpenClaw Bob agent**, not Ollama directly. First verify installed Gateway RPC/session/auth compatibility, then implement the smallest safe server-side bridge and mobile UI via `bobctl update`. Preserve all publishing, friend and memory safeguards.
