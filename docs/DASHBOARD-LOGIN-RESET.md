# Bob dashboard access: console login reset and mobile Settings style

The deployed v0.7.2 dashboard accepts HTTP Basic authentication and now loads the credential file for every authenticated request. When the operator forgets the original password, `scripts/set_dashboard_login.py` can securely replace both the dashboard username and password **from a local trusted OpenClawLab shell**, without needing the old password. It does not restart services or touch SQLite or Moltbook workers. It does not print, record in command history, or accept the new password as a command-line argument.

## One-command interactive reset

Run from **Windows PowerShell** (this opens interactive prompts, unlike a password inside a shell command):

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 scripts/set_dashboard_login.py"
```

Prompts: dashboard username (press Enter to keep existing), new password (minimum 20 characters), confirm new password. Characters are hidden. Passwords stay inside the private `~/.config/bob-system/lan-auth.json` file as existing format, mode 0600. Because Bob reloads credentials on each request, the old HTTP Basic username/password stops working immediately, without restarting the Activity Manager. Open a fresh private tab on phone or desktop if browser Basic-auth caching prevents a fresh login. No password should be pasted into this chat.

The script is deliberately **not** a web endpoint. It requires an interactive terminal as the `openclaw` Linux user and the ability to read the already-private credential file. Do not run it as root.

## Settings visual-only patch

`scripts/build_v072_settings_candidate.py` has an optional `styled=False` mode that exactly reproduces the first v0.7.2 manager already deployed. Default `styled=True` adds an accessible dark cyber-lab settings card, mobile full-width inputs, focus states and a blue button, while keeping the same navigation and routes. `scripts/patch_v072_settings_style.py` refuses nonmatching installed manager bytes and uses an explicit confirmation flag, private backup/journal, controlled service restart and health verification with code rollback if the patch fails. It never reads or writes the SQLite database.

Read-only preflight:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/patch_v072_settings_style.py"
```

Production style installation requires a separate explicit `--apply --confirm APPLY-BOB-SETTINGS-STYLE` invocation and restarts only the Activity Manager. If the patch records an incomplete transaction, operator recovery mode is `--recover --confirm RECOVER-BOB-SETTINGS-STYLE`. Do not repeat a refused patch without reviewing its journal.

The LAN HTTP endpoint remains unencrypted; use a trusted LAN/VPN or HTTPS reverse proxy, never an untrusted/public network.
