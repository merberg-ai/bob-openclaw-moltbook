# v0.7.0: Transient systemd experiment safety review (NOT AUTHORIZED)

## Gate just accepted

On the OMEN, the read-only systemd preflight passed after 106 tests. The systemd user manager was reachable, ten fixed staging names were absent in both user and system scopes (20 queries), required binaries were present, and no unavailable queries or collisions were reported. **No units were installed, registered, or started.**

## Why passing the preflight is insufficient

`systemd-run --user` creates and starts a real transient unit in the user's existing systemd manager. That would be the first service-manager change in this project. The preflight only proves that the names were free when checked, not that namespaces, permissions, resource controls or cleanup will function.

Upstream documentation warns that `PrivateNetwork=yes` for unprivileged per-user services depends on user-namespace support and may fail; see https://www.freedesktop.org/software/systemd/man/systemd.exec.html . `IPAddressDeny=any` is not a substitute for proof of effective network restrictions on a user manager. WSL also states that systemd services by themselves do not keep the WSL instance alive: https://learn.microsoft.com/en-us/windows/wsl/systemd .

## Proposed first real systemd experiment

**Not yet executable. No start command or installer is included in this phase.**

1. Run only one uniquely prefixed, nonpersistent, transient, *short-lived* mock service, under `openclaw`'s user manager. No timers, no Publisher, no Gateway/Ollama/Moltbook integration, no credentials, no live SQLite, and no production service dependencies.
2. Create all mock payload and state inside one private, auto-cleaned sandbox outside the live installation. Independently verify SHA-256, exact dummy-config schema, fixed argv, no symlinks, and fresh no-collision preflight immediately before registration.
3. Require `Type=exec`, `NoNewPrivileges=yes`, scoped process limits/timeouts, and a network-isolation mechanism whose support is demonstrated on the **actual OpenClawLab systemd version and kernel**. Abort if user namespaces or required restrictions are absent, ignored or ineffective. Never silently fall back to a network-enabled process.
4. Before any real service activation, review the exact transient unit property list and verify that each property is supported for `--user`, with deterministic nonsecret logs only. Prefer an additional isolated WSL test distribution if per-user network isolation cannot be confidently demonstrated.
5. Once explicitly authorized, observe the unit's exact stage-prefixed identity, successful execution and termination, cgroup/PID cleanup, and lack of unexpected unit registration. Use bounded timeouts and unit-specific cleanup, never `pkill`, wildcard stops, system-wide daemon reloads or changes to existing Bob units.
6. Capture only boolean/enum results: observed runtime state, namespace enforced, process exited, unit collected, private temp state removed, live services unchanged. Abort immediately if any guard is uncertain.

## Explicit approval boundary

**The operator must separately approve the exact real transient execution plan after network and cleanup safeguards have been reviewed.** No script in the currently approved preflight may call `systemd-run`, `systemctl start/stop/restart/enable`, `daemon-reload`, or alter the live service manager.

Remaining production updater gates include reviewing the unknown Gateway `[Service]` directive, exact drop-in ordering and command/environment reconstruction without publishing secrets, worker pause/drain and uncertain-publication handling, independent release health checks, and Windows cold-boot recovery. Current green tests do not close those gates.
