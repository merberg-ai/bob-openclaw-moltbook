## CH-HTTPS3 versioned production TLS-only cutover (owner-host prerequisite: Windows public CA trust imported)

The OMEN owner reports that the public `ca.crt` was imported successfully into the Windows trust store on the OMEN and the other primary LAN Windows computer. The public file's independently verified SHA256 is `af47c380af49eaf5b51683eb2cb1b6455eba019e754e09e295a0a3eeedc1f196`. Importing a certificate is **not** proof of a valid browser handshake; that will be tested only after CH-HTTPS3.

**Versioned code-only release:** `v0.8.0-chhttps1` → `v0.8.0-chhttps3`; exact listed files `bob_manager_tls.py` and `bob-activity-manager`; `restart_manager: true`. No database/schema operation, credential rotation, gateway/Scout/publisher service action or new port. Existing `192.168.1.24:18790` remains the only private-LAN web endpoint. The updater has an explicit reviewed transport mapping: existing CH1 HTTP before restart, candidate CH3 with verified CA/hostname HTTPS after restart, or old CH1 HTTP upon code-only rollback. The server refuses bad CA, wrong SAN, world-readable/symlinked key/cert, wrong account or TLS failure. No plaintext fallback.

### Owner preflight and deliberate versioned switch

Run from the `openclaw` WSL user (not `sudo`):

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/report_ch_https3_cutover.py --preflight
bobctl update --check
```

Require `acceptance: PASS` on preflight, and updater preview showing exactly `v0.8.0-chhttps3`, from `v0.8.0-chhttps1`, only two files `bob_manager_tls.py, bob-activity-manager`, with `Restart Activity Manager: True`. Do not proceed on any unexpected output. **There is no self-activating TLS switch.**

Then:

```bash
bobctl update
```

Type exactly `UPDATE` in the updater's interactive confirmation. The guarded updater makes a verified SQLite backup but must **never restore** that old DB as an update rollback. It replaces the two code files, restarts the *manager only*, validates all existing authenticated manager routes over CA-verified HTTPS, and commits the new installed registry only on success. If post-restart TLS health fails, the updater must code-rollback the prior files and revalidate HTTP over the old CH1 release. Review rollback output/journal before any retry; no manual publisher call. A successful install produces `BOB UPDATE: updated`.

Next, from the OMEN WSL user:

```bash
python3 scripts/report_ch_https3_cutover.py --installed
```

Require `acceptance: PASS`, installed exact hashes verified, R3 schema complete/Off, private CA SHA256 match, authenticated HTTPS manager health and authenticated R3 page, unauthenticated R3 returns 401 and **plain HTTP on port 18790 is refused**. This is read-only (it creates a temporary synthetic local TLS verifier socket for checking the certificate, not the live server). Confirm `https://192.168.1.24:18790/r3` loads without a certificate warning in Edge/Chrome on both OMEN and remote LAN computer. Check that normal R3 features remain displayed and do not click owner-mode enable controls. HTTP `http://192.168.1.24:18790/` must fail.

If WSL passes but the other LAN machine fails, treat it as a separate LAN/Windows portproxy/firewall/browser trust issue; do not weaken TLS, enable HTTP fallback or disable certificate checks. Keep the current code-only installation healthy and investigate.

### Remaining gates

CH-HTTPS4 is the final browser and LAN-only acceptance on both machines, Basic credential rotation after HTTPS, service/WSL/Windows reboot recovery, and later R3 canary review. **R3 real-send is still compiled Off**, even on a fully HTTPS Activity Manager. Any abnormal updater journal must be inspected before retries. Never reset live SQLite or historical send attempts to repair TLS.

---

## CH-HTTPS2 OMEN live owner acceptance (2026-10-31)

Owner preflight: `owner host: verified`, `ch https1 install: verified`, `certificate state: absent`, `eligible to prepare: True`. Owner typed `PREPARE BOB HTTPS`; local private certificate setup returned SANs for `192.168.1.24`, `127.0.0.1`, `localhost`, local TLS handshake and wrong-hostname rejection PASS. Subsequent `--verify` independently verified the CA/server chain, private key match, SANs and synthetic loopback TLS. The public `ca.crt` SHA256 is `af47c380af49eaf5b51683eb2cb1b6455eba019e754e09e295a0a3eeedc1f196`. The installed manager still listens in cleartext HTTP on its existing private LAN port; no send authorization occurred.

## CH-HTTPS3 source-only candidate, not a release (2026-10-31)

The separately reviewed `releases/candidates/ch-https3-tls-manager.json` names a **future** two-file code update from installed `v0.8.0-chhttps1` to `v0.8.0-chhttps3`: `bob_manager_tls.py` (new fixed private certificate validator, TLS-only listener, HTTPS-only origin enforcement), and the generated `bob-activity-manager` (pinned R3.13d builder output plus a single isolated TLS-only Handler subclass and `serve_tls` entry). `restart_manager: true` in **candidate only**. Neither old base source nor the existing R3 publisher changes. The manager validates exact private CA/leaf cert chain, SANs including updater loopback IP 127.0.0.1, and restrictive owner permissions **before binding**. Server context minimum TLS1.2, no HTTP fallback, no public reverse proxy. All legacy POST handlers and independent R3 actions use true `https://` same-Origin/Referer and existing CSRF. CI builds the candidate and tests real TLS on **ephemeral localhost** with fake credentials and private fixture certificates, legacy/R3 GET, HTTPS POST Origin rejection, wrong CA and plaintext refusal.

**Promotion is blocked** until the owner explicitly confirms Windows public CA fingerprint matching and Current User Root trust. Even then, source-only CI acceptance does not equal production cutover authorization. Next deliverable: independent CH-HTTPS3 read-only TLS post-install report and exact updater code-only rollback rehearsal. Public Moltbook R3 canary and automatic publishing remain Off.

---

## CH-HTTPS1 OMEN operator acceptance and CH-HTTPS2 local certificates (2026-10-31)

The owner reported **CH-HTTPS1 installation acceptance PASS** on the OMEN: `installed release: verified`, R3 source Off verified, `r3 schema: ready`, migration journal complete, current manager authenticated HTTP healthy, future strict TLS transport recognized, authenticated `/r3` page accepted. No changes to services, database, publisher, or R3 permissions.

### CH-HTTPS2 separate certificate gate (no service/release update)

**Scope:** private certificate material only, generated on the actual OpenClawLab WSL instance. No new installed code release, dashboard restart, second LAN port, firewall change, Windows trust import or Bob/Moltbook send permission.

After this source-only PR is reviewed, CI passes and merges into `next`, run under the normal `openclaw` account:

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/prepare_ch_https2.py
```

Expected: `owner host: verified`, `ch https1 install: verified`, `certificate state: absent`, `eligible to prepare: True`. This is strictly read-only.

Then the separately approved local certificate-creation operation:

```bash
python3 scripts/prepare_ch_https2.py --apply
```

It requires typing **`PREPARE BOB HTTPS`** in the interactive terminal. It creates private, owner-only, no-symlink, no-overwrite files inside **`/home/openclaw/.config/bob-system/manager-tls`**. The CA uses an ECDSA P-256 signing key and a five-year trust certificate, and issues a one-year ECDSA P-256 TLS server certificate with verified SANs `192.168.1.24`, `127.0.0.1`, and `localhost`. It checks CA and leaf roles, key/public certificate match, 30+ remaining days, OpenSSL chain verification for all three SANs and a **real disposable authenticated HTTPS loopback socket** (plus rejection of a wrong hostname). The live Activity Manager on 18790 is **not** restarted or modified. The CA private key `ca.key` and leaf private key `server.key` remain mode 0600 in WSL and must **never** be copied to Windows, the other laptop, Git, a chat or a web server.

Recheck without writing files:

```bash
python3 scripts/prepare_ch_https2.py --verify
```

Expected: `CH-HTTPS2 CERTIFICATE ACCEPTANCE: PASS (READ ONLY)`, all three SANs and loopback TLS verified; public CA file and public CA SHA256 printed. After generation, a no-argument `prepare_ch_https2.py` intentionally says `existing_do_not_overwrite` and refuses to create a second CA. Use `--verify` instead. On failure, keep the original HTTP manager running and do not delete/recreate private material blindly.

### Windows CA trust, *after* cert generation and fingerprint verification

This is a deliberate **owner action**, never performed by the certificate script. The public CA file alone is safe to copy or inspect; the CA private signing key must remain in the WSL account. On the OMEN Windows machine, the file is reachable through the WSL share at:

```text
\\wsl.localhost\OpenClawLab\home\openclaw\.config\bob-system\manager-tls\ca.crt
```

In PowerShell, compute its SHA256 **before importing**:

```powershell
Get-FileHash '\\wsl.localhost\OpenClawLab\home\openclaw\.config\bob-system\manager-tls\ca.crt' -Algorithm SHA256
```

Compare against the full **public CA SHA256** from `--verify` (case-insensitive). **Do not import if the hashes disagree.** If verified, explicitly import the *public CA only* into **Current User → Trusted Root Certification Authorities** using Windows certificate import or the owner-approved `certutil -user -addstore Root <ca.crt>` command. Root trust grants that CA broad certificate-signing authority on the Windows user account. **Only do this for your own private CA and on systems you control.** Browsers using their own trust store (for example some Firefox configurations) may need separate trust settings. A second LAN laptop needs the verified public CA certificate securely copied to that computer and deliberately trusted there too; no access to the WSL private CA key.

Windows trust cannot be considered proven until the later CH-HTTPS3 TLS-only listener is running and the browser opens `https://192.168.1.24:18790/r3` **without any bypass/warning**, validates the exact host and prompts for existing Bob authentication. Do not test browser HTTPS on the live HTTP port until CH-HTTPS3 has been installed.

### Next boundary

**CH-HTTPS2 generates certificate bytes only.** The Activity Manager, updater and `bobctl` stay on the accepted CH-HTTPS1 HTTP mode. CH-HTTPS3 must separately update the generated Manager to wrap its existing socket with a TLS server context (minimum TLS1.2, no HTTP fallback), change existing Origin/Referer checks to strict HTTPS, and pass authenticated read-only R3 and legacy routes with TLS. The guarded updater must prove the candidate HTTPS listener and roll back to the original verified HTTP release on failure. **Never restore old SQLite or enable Bob-R3 comment publishing as part of any TLS step.**

---

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
