## CH-HTTPS0 OMEN owner acceptance (2026-10-31)

The owner ran the read-only CH-HTTPS0 report on the actual OMEN. It returned `installed release: v0.8.0-r3stage1`, `r3 schema: ready`, `migration journal: complete`, manager/publisher/Scout timers `active`, `current manager transport: authenticated_http_r3`, `listener: lan_or_wildcard`, `certificate state: not_prepared`, and `source preflight: pass`. No live services, database, certificate or publication settings were modified.

## CH-HTTPS1 transport-aware code-only release candidate

**Exact chain:** `v0.8.0-r3stage1` → `v0.8.0-chhttps1`.

**Exact files:** `bob-release-updater` and `bobctl`. `restart_manager: false`. The Activity Manager executable and its existing HTTP-only listener on the same LAN port stay **unchanged**, as do Gateway, Scout, publisher, timers, R3 SQLite tables and Off settings.

The updater now uses explicitly reviewed installed/current/candidate/restored release IDs to choose health-check protocols. Existing stage1 and CH-HTTPS1 check over HTTP (because the manager is still HTTP), while the future separately reviewed CH-HTTPS3 health checks use **CA-verified HTTPS** with minimum TLS 1.2 and an IP SAN for `127.0.0.1`. The CA path is fixed to `~/.config/bob-system/manager-tls/ca.crt`, ownership/mode checked and never printed. A failed HTTPS handshake, hostname validation or CA validation must not retry plaintext HTTP. No environment variable or forwarded request header may decide transport. `bobctl` independently checks the installed manager's updater-registry SHA before selecting transport.

### Owner install gate after reviewed CI and PR merge

Run these as the existing `openclaw` user without `sudo`:

```bash
cd ~/bob-next && git pull --ff-only
bobctl update --check
```

Confirm the exact target version `v0.8.0-chhttps1`, exactly `bob-release-updater,bobctl`, and `Restart Activity Manager: False`. If any field differs, stop. Then:

```bash
bobctl update
```

At the existing trusted updater prompt, type exactly `UPDATE`. This is the established code-only rollback/backup/lock procedure. **Do not** change the manager unit, install a certificate, disable R3 source gates, open a new port or add a reverse proxy.

Read-only post-install report:

```bash
python3 scripts/report_ch_https1_installed.py
```

Expect `installed release: verified`, `R3 off source gates: verified`, `R3 schema: ready`, `migration journal: complete`, `current manager transport: http_pre_cutover`, `future tls transport: verified_strict_https`, `authenticated manager health: pass`, `authenticated r3 page: authenticated_read_only_page`, and `installation acceptance: PASS`. The dashboard will still show **HTTP / Not secure** until the independently approved CH-HTTPS3 cutover. This does not authorize any new R3 post, TLS mode switch, manual owner mutation or public canary.

The previous `report_r313d_stage1_installed.py` and `report_ch_https0.py` specifically attest their earlier release IDs and are historical after CH-HTTPS1. Use `report_ch_https1_installed.py` for the new installed release.

**Next:** CH-HTTPS2 local certificate/private CA trust and CH-HTTPS3 separate review, with rollback and Windows client acceptance. Never paste or publish a CA signing key, dashboard password or certificate private key.

---

# CH-HTTPS: Bob Activity Manager HTTPS-only LAN hardening

**Scope:** existing authenticated Activity Manager on the OMEN/OpenClawLab WSL instance, currently accessed at `http://192.168.1.24:18790`. Preserve the same IPv4 address, TCP port, UI routes, existing user account and LAN-only exposure. Do **not** use a public reverse proxy, open WAN firewall rules, expose Bob's Gateway, change publisher credentials, or enable R3 comments as part of TLS work.

## Verified architectural constraints

The generated Activity Manager currently serves `ThreadingHTTPServer` over ordinary HTTP and authenticates LAN requests using HTTP Basic credentials from the owner-private `~/.config/bob-system/lan-auth.json`. Its strict Host/Origin/CSRF checks are currently HTTP-specific. It also exposes read-only R3 owner controls after the accepted default-Off live SQLite schema migration.

The installed guarded updater authenticates its before/after and rollback GET health checks via `HTTPConnection("127.0.0.1",18790)`. `bobctl` manager diagnostics also use `http://127.0.0.1:18790/healthz`. **An immediate HTTPS-only manager release would cause these components to report false downtime and could trigger code rollback.** It is not safe to rebind the existing port through an unreviewed proxy or create a second plaintext LAN port. There is also an exact `http://` check in the existing Manager's browser Origin/Referer validation that would reject legitimate HTTPS POSTs after a naive SSL socket wrap.

Use the established versioned update channel and the pinned generated dashboard build chain. Keep the legacy publisher executable, timer, Scout, R2 shadow ZIP and persisted SQLite unchanged.

## Phases and explicit gates

| Gate | Owner-visible result | Live impact |
|---|---|---|
| **CH-HTTPS0**: Read-only inventory | `python3 scripts/report_ch_https0.py` verifies the installed R3 schema/journal, owner account, stage1 executable hashes, authenticated localhost /r3, LAN listener, timers, and absence/presence of TLS materials | **None.** This report only reads metadata and makes one authenticated local GET |
| **CH-HTTPS1**: Transport-aware updater preparation | Separately reviewed versioned release teaches `bob-release-updater`, `bobctl` and installation checks to validate an exact HTTPS transport and client CA while retaining the existing HTTP mode *only* for the current explicitly attested pre-switch release; tests prove post-switch and rollback health probes are phase-specific | One owner-typed code-only `bobctl update`; no TLS switch |
| **CH-HTTPS2**: Trust and certificate provisioning | Generate a private local CA and short-lived server cert with Subject Alternative Names for `192.168.1.24`, `127.0.0.1`, and `localhost`, or use a valid DNS-01-acquired certificate for a split-DNS private domain. Verify key/cert match, SAN, validity, private permissions and authenticated local TLS handshake in a disposable socket. Public CA certificate is installed/trusted explicitly on each browser client; **never export the private CA key**. Browser trust verification is a separate operator check | Private certificate files only; original HTTP manager remains unchanged |
| **CH-HTTPS3**: Guarded TLS-only switch | A separate code-only reviewed release wraps the **same** Activity Manager socket in `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)`, TLS 1.2 minimum, with fixed private PEM/key; has **no LAN HTTP fallback**. Update strict Origin/Referer checks to exact HTTPS and test all POST protections. Updater must verify HTTPS health with trusted CA and hostname before committing. On failure, use reviewed code rollback and original HTTP release health check | Brief manager restart only; no database migration, Scout, Gateway or publisher unit change |
| **CH-HTTPS4**: Browser/network acceptance | Windows OMEN and second LAN laptop can open `https://192.168.1.24:18790/r3` with a trusted certificate; Basic auth, CSRF, exact Host, HTTPS Origin work. **A plaintext HTTP request to the same LAN port is refused**. After verifying client access, rotate the historical LAN password using a separately reviewed workflow and recheck all clients | Owner-reviewed authentication change only; do not enable R3 posting |

**Stop / rollback rule:** Never mark HTTPS accepted because a port is open or a certificate file exists. Require an authenticated TLS 1.2+ handshake with a valid trusted cert and matching IP SAN, healthy legacy routes, and a confirmed failure of plaintext LAN HTTP. If any step fails, retain the R3 publishing Off gates and inspect the code-only updater journal. Never restore a stale SQLite DB as an HTTP/TLS rollback.

## CH-HTTPS0 instructions

As the normal `openclaw` account in OpenClawLab, after this source-only PR merges into `next`:

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/report_ch_https0.py
```

Expected on the accepted current host: `installed release: v0.8.0-r3stage1`, `r3 schema: ready`, `migration journal: complete`, Activity Manager and both user timers `active`, `current manager transport: authenticated_http_r3`, `certificate state: not_prepared`, and `source preflight: pass`. The listener classification normally shows `lan_or_wildcard`; it is metadata, not a claim that the port is WAN-accessible. Some benign platform differences may report `unverified` for listener state; that requires checking the OS but does not alter anything.

**Do not run a certificate generator or restart the manager at CH-HTTPS0.** The current HTTP endpoint is still plaintext; don't submit new sensitive owner actions on it. The next source change is the transport-aware updater, not the HTTPS-only manager itself.

## Design and operating decisions

- Keep direct TLS on the existing manager port. A reverse proxy on another host would still carry Basic-auth credentials over unencrypted OMEN LAN unless the upstream were also protected, which defeats the simple deployment goal.
- Use private, owner-restricted certificate material under `~/.config/bob-system/manager-tls/`; no key in Git or printed by diagnostics. A local private CA is feasible for fixed RFC1918 IP addresses but must be explicitly trusted on *each* Windows browser. Trusting a local CA carries its own responsibility; protect its signing key and rotate certificates. A publicly trusted DNS certificate via DNS-01 is an alternative if a private DNS name is preferred later.
- The manager must either successfully start with verified TLS settings or **fail closed**. Never auto-fallback to HTTP when LAN binding is enabled after the switch.
- Preserve strict Host, same-origin HTTPS and CSRF checks, and never treat an untrusted `X-Forwarded-Proto` header as proof of TLS. No wildcard Host/Origin acceptance and no new public listen socket.
- R3 real comment dispatch remains compiled Off. HTTPS protects the owner-control interface; it does **not** authorize Bob to publish.

## Acceptance boundary

CH-HTTPS0 establishes readiness **for development of CH-HTTPS1**, not proof of actual HTTPS security. No versioned release manifest changes, no installed executable changes, no Windows trust-store changes and no post/credential permissions are part of this phase.
