# v0.7.1: Safe browser preview (synthetic data only)

**Purpose:** Inspect the real generated v0.7.1 responsive Activity Manager in a Windows browser **before** requesting a controlled production update. This preview does not install files, start or restart systemd units, access Bob's real database, or publish anything.

## One PowerShell paste on OMEN

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "set -e; if [ ! -d ~/bob-v071-preview/.git ]; then GIT_TERMINAL_PROMPT=0 git clone --branch feature/v0.7.1-navigation --single-branch https://github.com/merberg-ai/bob-openclaw-moltbook.git ~/bob-v071-preview; fi; cd ~/bob-v071-preview; GIT_TERMINAL_PROMPT=0 git pull --ff-only; python3 scripts/preview_v071_ui.py"
```

Then open the printed `http://127.0.0.1:<port>/` URL in a browser on the **same OMEN**. Browse Scout & review, Published activity, and Original posts. Resize the browser or open its mobile-device emulator to inspect the desktop sidebar, mobile menu, long draft wrapping and touch target sizing.

**Stop the preview with Ctrl+C** in the original PowerShell terminal. The script uses a private temporary directory and automatically deletes the preview database, code and dummy records when it finishes.

If the printed loopback URL is not reachable from Windows because of WSL networking settings, stop the preview and review your localhost forwarding setup. Do not change the bind address to `0.0.0.0` or expose the mock server to the LAN.

## Safety controls

- The candidate is built from the SHA-256 pinned existing Activity Manager source plus the exact navigation module, and the two-file review package manifest is rechecked.
- The script starts a **separate child Python process** with a new private `HOME`, a minimal environment with no inherited API keys or proxy settings, and only the checked candidate plus existing pinned local modules.
- The child binds **only** to `127.0.0.1` on an OS-selected ephemeral port. Its Host allowlist is restricted to that particular listener.
- A preview-specific handler **always returns HTTP 405 for POST**, including Approve, Reject, Publish, original draft generation and verification. The preview also visibly displays `DEMO PREVIEW ONLY` on all three pages.
- A sample scout post, a dummy published comment and reply, an original-post draft, a completed draft request and an activity event are stored in a **synthetic SQLite database** under the temporary HOME. No real post ID, credential or Moltbook content is imported.
- The parent waits while the preview is open. Closing with Ctrl+C removes the temporary home and code. No background service is installed or persistent process configured.

## Automated acceptance

CI executes `python3 scripts/preview_v071_ui.py --self-test`. This starts and stops the same isolated server, verifies all four GET routes, checks sample content, rejects publishing POST with HTTP 405, rejects untrusted Host with HTTP 403, and verifies cleanup. The synthetic preview and its script have additional regression coverage.

**Limit:** A correct synthetic preview does not prove the real LAN authentication, the actual operator's mobile-browser experience, or systemd production deployment. Those are separate gates. The currently generated v0.7.1 ZIP is still deliberately marked **non-deployable**.
