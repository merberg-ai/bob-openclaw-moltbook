# Bob Activity Manager v0.7.2: one-command upgrade from installed v0.7.1

The operator confirmed the v0.7.1 production deployment and visually verified its responsive mobile menu. Its displayed "v0.6" label came from the pinned legacy renderer and did **not** mean v0.7.1 was missing. The v0.7.2 candidate now updates every inherited version marker and adds Settings and System Status.

`scripts/update_v072_dashboard.py` is a **version-specific production updater**, not a generic GitHub sync or a modification made by `git pull`. It expects the exact installed v0.7.1 manager and navigation module. It stages the new manager, updated navigation, password backend and live-status backend as four regular files. It refuses drift, reads the effective user-systemd contract, authenticates existing local HTTP, checks private LAN auth permissions, creates and restore-verifies a fresh private SQLite backup automatically, records a durable local journal, installs code, restarts only the Activity Manager, verifies authenticated `/settings`, `/system/status`, `/api/system/status`, the existing routes and v0.7.2 version label, and restores v0.7.1 code if the new UI fails. It does not write SQLite or change credentials during installation.

## Operator workflow

**No deployment authorization is implied by the existence of this script.** It changes production only with `--apply --confirm UPGRADE-BOB-V072`. Do not execute that mode until the owner explicitly approves the v0.7.2 live upgrade.

Read-only readiness (does not execute the 308-test suite or create a backup):

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/update_v072_dashboard.py scripts/build_v072_settings_candidate.py && python3 scripts/update_v072_dashboard.py"
```

The update mode, **after explicit approval**, is the same script with `--apply --confirm UPGRADE-BOB-V072` instead of the default read-only mode. It performs its own preflight and automatic backup, so no second backup command or separate 308-test invocation is required. Save its printed private backup pathname privately.

If an upgrade crashes partway through code installation, `--recover --confirm RECOVER-BOB-V072` attempts to restore the known original v0.7.1 code after validating the journal and all installed bytes. A terminal `incident` or `complete` journal is deliberately not automatically retried. Do not repeatedly invoke apply when a transaction has been created.

The Settings password change uses the old password, a new password of at least 20 characters, a confirmation, and CSRF/origin checks. The old password ceases authenticating as soon as rotation completes. Browsers may cache Basic authentication; new private tabs can help re-prompt. Current HTTP LAN traffic is **not encrypted**; use a trusted LAN/VPN or HTTPS rather than exposing it publicly.

This release script itself has not yet been run on the operator's OpenClawLab host. It is a code artifact for the next explicitly approved upgrade; do not describe it as already installed.
