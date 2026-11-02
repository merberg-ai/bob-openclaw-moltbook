# v0.7.0 Phase 6: Import the reviewed Bob source into the development checkout

Operator submitted a private ZIP (`bob-source-candidate-v070.zip`) and its SHA-256 manifest was verified against all nine source files. The only change to installed code is masking two runtime password displays in `bin/bob-lan-config` (lines 39 and 44).

Security review: no embedded API keys or LAN passwords were found; this is source review, **not** proof of absence of any sensitive information. Script imports use Python stdlib and local Bob modules; runtime still requires systemd, Docker, OpenClaw, Ollama and Moltbook API access when deployed. The imported source must not execute in tests or on the production machine until the staging/release gates pass.

## One PowerShell block from the Windows OMEN

The reviewed ZIP is already at `D:\SRC\bob-source-candidate-v070.zip` on the operator's Windows machine. The WSL distro does not expose the D: drive reliably, so this block sends Base64-encoded bytes on stdin (never as CLI arguments). It does not print the Base64, upload the ZIP or use WSL drive mounts.

~~~powershell
$zip = 'D:\SRC\bob-source-candidate-v070.zip'
if (-not (Test-Path $zip)) { throw "Missing reviewed source ZIP: $zip" }
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && git pull --ff-only"
if ($LASTEXITCODE -ne 0) { throw 'Git update failed; import not started.' }
[Convert]::ToBase64String([IO.File]::ReadAllBytes($zip)) | wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && python3 scripts/import_verified_sources.py --stdin-base64"
if ($LASTEXITCODE -ne 0) { throw 'Source import refused.' }
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && python3 -m unittest discover -s tests -p 'test_*.py' -q && git status --short"
~~~

The import helper refuses unexpected archive members, symlinks, invalid manifest or SHA-256 hashes, unreviewed source bytes, Python syntax errors, the wrong Git branch, dirty worktree, or an existing `src/` directory. It writes source into `~/bob-v070-inventory/src/bin` and `src/lib/bob` with safe file permissions. It does not write anything under `~/.local/bin`, the live SQLite database, credentials files or systemd service paths. It does not call Moltbook, start services, commit or push to GitHub.

Expected output after success: 9 source files imported into DEVELOPMENT checkout; password mask confirmed; local offline regression tests pass, and `git status --short` shows new `src/` files. If any error occurs, copy only the console error text, not raw ZIP or credentials.

**Do not run these scripts as daemons or replace any live binaries yet.** After local tests, the source diff and new service templates need review before Git commit/push. Full staging update, backup/rollback and v0.6+ acceptance tests are still required for a production release.
