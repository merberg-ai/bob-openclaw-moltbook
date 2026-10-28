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
