# v0.7.0 Phase 5: Export a review candidate, never a live deploy

The source review finished with 9 Python files, no detected external imports and three print-related warnings. Two in bin/bob-lan-config (lines 39, 44) display the password retrieved from the credentials JSON file; one in bobctl (line 453) uses static literal arguments only. No hardcoded credentials were detected by the heuristic scanner, but static scanning cannot guarantee all secrets are absent.

**DO NOT commit or push this candidate ZIP to the public repository.** It is an intermediary for local/manual inspection. It contains only the nine SHA-pinned code files from the private archive plus a manifest. The tool does not add systemd configuration, credential files, database contents, feed data, process environment, private memory or logs.

## One PowerShell command (from the operator's Windows machine)

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && git pull --ff-only && python3 scripts/prepare_source_candidate.py --destination /mnt/d/SRC/bob-source-candidate-v070.zip"
~~~

**If /mnt/d/SRC does not exist in WSL, the explicit destination will fail.** This is common with WSL automount differences. The script now explains that failure instead of printing only `FileNotFoundError`. The file must not already exist; the tool refuses overwrites. Do **not** create or mount Windows drives just to perform this export.

### Recommended Windows-to-WSL fallback (no /mnt/d, UNC, wslpath, or remounts)

Paste the complete block below in PowerShell. It creates the ZIP in WSL's private directory, then reads it as Base64 and writes the same bytes to `D:\\SRC` through Windows PowerShell's .NET file API. Raw Base64 is held in memory and not printed to the console. The source archive never goes to GitHub.

~~~powershell
$run = @(wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && git pull --ff-only && python3 scripts/prepare_source_candidate.py")
$exit = $LASTEXITCODE
$run
if ($exit -ne 0) { throw "WSL source candidate creation failed." }
$zip = (($run | Where-Object { $_ -like 'Review ZIP created:*' } | Select-Object -Last 1) -replace '^Review ZIP created:\s*','').Trim()
if (-not $zip) { throw "Missing review ZIP path." }
$data = @(wsl -d OpenClawLab -u openclaw -- base64 -w0 $zip)
if ($LASTEXITCODE -ne 0 -or $data.Count -eq 0) { throw "Cannot transfer ZIP bytes." }
$target = 'D:\\SRC\\bob-source-candidate-v070.zip'
if (Test-Path $target) { throw "Refusing to overwrite: $target" }
[System.IO.File]::WriteAllBytes($target, [Convert]::FromBase64String(($data -join '')))
Get-Item $target | Select-Object FullName, Length
~~~

The utility also refuses any content drift from the known baseline, unexpected risks in the static audit, and any new credential-like literal matches after masking. If it fails, share **only the error text**, not the raw archive.

Success shows exactly 9 source files, and states that password output was masked in the exported copy only. The original scripts, live database, systemd, credential file and services remain untouched. This candidate is not runnable/deployable and has not passed Bob's app-level regression tests.

Archive name: bob-source-candidate-v070.zip in D:\SRC. It is intended for operator-controlled, private review and further sanitization, **not** for publication. The Windows destination uses Windows ACLs, so avoid shared/public folders or cloud sync. Once the operator decides to provide it to the assistant for review, treat it as private source material. Manual inspection of all files is required before any code is committed to public GitHub.

## What the export changes

- Rewrites only the two known password stdout statements in bin/bob-lan-config, lines 39 and 44, to print [masked] in the source candidate.
- Leaves all other code bytes unchanged, preserving per-file hashes in REVIEW-MANIFEST.json.
- Does not modify LAN credentials, enforce password rotation, add UI users, or alter the actual running helper.
- Password reveal and bootstrap UX needs a deliberate design and regression testing before any deployment.

## Next engineering gate

Review every script in the private candidate for literal configuration, credential handling, network API boundaries and startup dependencies. Import source in a standalone development tree with synthetic tests, and only then plan a staged installation and rollback test. See #1 and #3.
