# Bob architecture and trust boundaries

**Current implementation:** v0.7.2 installed on the operator's Windows 11 / OpenClawLab WSL2 system. Reviewed application sources are merged into GitHub `main`. The host's existing updater was installed successfully; the operator reports the canonical `main` release-channel migration completed successfully. A fresh-host installer remains unbuilt.

## Runtime architecture

```text
Windows 11 OMEN
  Ollama (qwen3.5:9b)                 Docker Desktop
         |                                  |
OpenClawLab (WSL2, systemd user services)
  OpenClaw Gateway 127.0.0.1:18789 -- restricted Docker sandbox
         |
  Moltbook scout -> sanitized feed -> agent draft -> source validation
                                                  |
                       human review or separately enabled auto-comments
                                                  |
  host publisher -> bounded queued POST -> Moltbook verification / public check
         |
  private SQLite queue, event history, replies and original post drafts
         |
  Activity Manager HTTP 127.0.0.1:18790 (optional trusted LAN)
      desktop/mobile navigation, Settings, Original Posts,
      Publishing Activity and live 15-second System Status
```

- **Scout:** Retrieves bounded public discussions, validates their IDs and drafts, and sends only sanitized untrusted data to the sandboxed local agent. Reports observed job stages.
- **Publisher:** Owns Moltbook credentials. Submits a queued comment only after the appropriate manual decision or separately enabled autonomous policy, with two attempts per UTC day and at least one hour between attempts. Manual decisions have queue priority. Ambiguous or unconfirmed outcomes are not silently retried.
- **Original posts:** Draft generation uses the local agent, accepts explicitly structured responses and validates them; publication still requires separate human approval. Challenges and visibility tracking remain separate from outbound comment counts.
- **Activity Manager:** Serves authenticated local/LAN pages; controls review and approval routes using origin, CSRF, session, input and digest constraints. Shows live service/worker status without inventing progress, and distinguishes an API acknowledgment from independently observed public comments.
- **Private state:** `~/.config/moltbook/activity-queue.sqlite3`, feed/report files, job checkpoints and per-host credentials are outside Git. The updater keeps its private manifest registry and rollback archives under `~/.local/state/bob-updater`.

## Trust boundaries

Moltbook posts and model outputs are untrusted **data**, never instructions to grant host access, mutate policy, change credentials or edit the agent's identity. The sandbox does not contain the Moltbook API key. The dashboard and publisher run as separate processes but currently share the same Linux user, **not** independent OS security identities. HTTP Basic over plain LAN HTTP is unencrypted; use a trusted LAN/VPN or HTTPS reverse proxy and don't expose to the internet.

Autonomous **comments**, original **posts**, and follow-up **replies** have separate authorization domains. Neither a response from Moltbook nor the presence of a valid comment ID proves the item is publicly visible. Public visibility audits remain read-only. The existing publisher stores its intent before POST and does not attempt blind retries.

## Versioned operations and planned work

`bobctl update` is a manifest-driven, explicit-confirmation updater. It checks the correct GitHub branch, release chain and installed file checksums, backs up SQLite before a nonempty change, installs code atomically, checks authenticated health and attempts a code-only rollback on failure. The installed updater now tracks canonical `main` following the operator-confirmed [main migration](MAIN-UPDATER-MIGRATION.md). Git `main` is canonical source; source history does not automatically mutate the running host.

**Next:** Deploy compact Scout/Activity polish (reviewed `v0.7.2-compact1`), then design a guided clean WSL/Windows installation workflow. The real manifest-driven update process is operator-verified. Source-linked observations, opinions, reflections and conversation continuity are v0.7.3+ roadmap work, **not currently shipped capabilities**. See [roadmap](ROADMAP-v0.7.md) and [installation status](INSTALLATION-STATUS.md).
