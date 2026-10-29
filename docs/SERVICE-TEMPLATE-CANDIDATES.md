# v0.7.0: Private, sanitized service-template candidates

**Status:** read-only baseline capture for manual review; NOT a deployable systemd configuration or production updater.

## Why we need this

The live host has 15 systemd unit files/drop-ins across 12 scope-qualified units, with user-scoped Gateway and Activity Manager services running and four user timers waiting. A disabled system-level Moltbook scout service and timer remain installed but inactive. We need to capture **actual unit semantics** before recreating systemd templates from GitHub. Copying raw unit bodies to a public repo is prohibited because they may embed command arguments, environment values or private paths.

## Read-only capture, from Windows PowerShell

After the v0.7.0 feature checkout is clean and current, run:

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && GIT_TERMINAL_PROMPT=0 git pull --ff-only && python3 scripts/prepare_service_template_candidates.py --topology-report /home/openclaw/.local/state/bob-baseline/inventory-20261028T144113282656Z-93497.json"
~~~

The tool independently opens each original file without following symlinks and checks its SHA-256 against the **private, 0600** topology inventory. Any changed, ambiguous, unreadable, unrecognized or unexpected entry causes refusal. It does not call systemctl or change any services, timers, credentials, login settings or live database.

The only output file is a new private mode-0600 ZIP under `~/.local/state/bob-baseline/service-reviews` (mode 0700), containing non-deployable `*.template.txt` candidates and a review-only manifest. No original unit file bodies are included. Every command (`Exec*`), environment, credential, working directory, username and private path **value** is omitted; only allowlisted, validated unit names, dependencies, timer schedules, service types, conservative security booleans and counts of withheld directives are present. Arbitrary directive values and unrecognized calendar words are not exported.

**Never install or enable the generated files**; they contain `ExecStart=@REVIEW_REQUIRED_NOT_DEPLOYABLE@` placeholders, and important values were intentionally removed. They are starting points for manual reconstruction and verification, not ready-to-run definitions.

## Operator acceptance

1. Confirm the tool prints the expected 15 files/drop-ins and `Deployable: NO`. Do not publish the private JSON report or any original `.service`, `.timer` or `.conf` files.
2. Inspect the generated candidate ZIP locally for unexpected host-specific strings, secrets or suspicious fields before sharing it privately for review.
3. After review, we can compare the candidate structures against the known-good service-state matrix and construct versioned, independently testable templates with explicit paths, dummy credentials, real timers and staging-only service names.
4. The follow-on staging installation must run outside the live `~/.local/bin`, user/system systemd roots and SQLite state, must not contact Moltbook, and must prove rollback before a production deployment is considered.

**If the extractor refuses**, leave production untouched. The console gives a failure class rather than echoing file content. We will use that classification to adjust the private audit procedure instead of removing security checks.

## Next gate: independent private ZIP audit and operator-controlled transfer

The operator ran the exact-source capture on 2026-10-28: 60 local tests passed, and 15 files/drop-ins were exported to the private archive `~/.local/state/bob-baseline/service-reviews/bob-service-candidates-20261028T151639870944Z.zip`. The tool reported `Deployable: NO`, with live services and credentials untouched. This is a private operator result, not an externally reviewed or deployable artifact.

An independent auditor, `scripts/audit_service_candidate_zip.py`, validates the existing ZIP against the same private inventory, with a separately implemented allowlist for the exported text format. It checks source hashes, exact member identities, non-deployable markers, safe directives, withheld counts, and private file permissions; it never invokes the installed units. CI passes 69 offline synthetic tests, followed by the nine-file isolated rehearsal. Passing this automated gate is not proof that a ZIP is free of secrets; review its contents before publication.

From Windows PowerShell, this one block performs the private check first and copies the archive to a **Windows user-local private review folder** only on success, using Base64 transfer because this WSL environment may not expose the D: mount:

~~~powershell
$source = '/home/openclaw/.local/state/bob-baseline/service-reviews/bob-service-candidates-20261028T151639870944Z.zip'
$topology = '/home/openclaw/.local/state/bob-baseline/inventory-20261028T144113282656Z-93497.json'
wsl -d OpenClawLab -u openclaw -- bash -lc "set -e; cd ~/bob-v070-inventory; GIT_TERMINAL_PROMPT=0 git pull --ff-only; python3 scripts/audit_service_candidate_zip.py --archive $source --topology-report $topology"
if ($LASTEXITCODE -ne 0) { throw 'Private service ZIP audit failed; no transfer performed' }
$destinationDir = Join-Path $env:LOCALAPPDATA 'BobBaseline'
[IO.Directory]::CreateDirectory($destinationDir) | Out-Null
$destination = Join-Path $destinationDir 'bob-service-candidates-reviewed-v070.zip'
if (Test-Path -LiteralPath $destination) { throw 'Review copy exists; refusing overwrite' }
wsl -d OpenClawLab -u openclaw -- bash -lc "base64 -w 0 $source" | ForEach-Object { $encoded = $_ }
if ($LASTEXITCODE -ne 0 -or -not $encoded) { throw 'Private ZIP transfer failed' }
[IO.File]::WriteAllBytes($destination, [Convert]::FromBase64String($encoded.Trim()))
wsl -d OpenClawLab -u openclaw -- bash -lc "sha256sum $source" | ForEach-Object { $linuxHash = ($_ -split " ")[0] }
if ($LASTEXITCODE -ne 0 -or (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $linuxHash) {
    Remove-Item -LiteralPath $destination -Force
    throw 'ZIP transfer hash mismatch; review copy discarded'
}
Write-Host ('Private Windows review copy: ' + $destination)
Write-Host 'Hash verified. Not published or installed; manual review still required.'
~~~

**Important:** `$source` and `$topology` are known literal paths from the successful operator captures, not secrets. In the runbook above the Linux command references PowerShell variables inside double quotes; this interpolates them on Windows, and neither path contains shell metacharacters. Do not generalize this snippet to arbitrary untrusted paths.

The operator should inspect the resulting copy locally and, if comfortable, attach the **sanitized candidate ZIP** in this private conversation for detailed manual review. Do not commit it to the public repository or run `systemctl` against its placeholder files. The original raw unit definitions and private topology report must never be uploaded.
