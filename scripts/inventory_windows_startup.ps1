#Requires -Version 5.1
<#
Read-only Windows startup discovery for Bob/OpenClawLab.
No scheduled tasks, registry entries, shortcuts or WSL settings are altered.
Never records command arguments, full paths, environment values or credentials.
#>
[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $env:LOCALAPPDATA 'BobBaseline')
)

$ErrorActionPreference = 'Stop'
$markers = '(?i)(OpenClawLab|openclaw|moltbook|bob[-_]activity|bob[-_]startup|bobctl|bob[-_]moltbook)'
$matched = [System.Collections.Generic.List[object]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

function Get-CommandCategory([string]$executable) {
    if ([string]::IsNullOrWhiteSpace($executable)) { return 'none' }
    $value = $executable.ToLowerInvariant()
    if ($value -match '(?:^|[\\/])wsl(?:\.exe)?$') { return 'wsl' }
    if ($value -match '(?:^|[\\/])(?:powershell|pwsh)(?:\.exe)?$') { return 'powershell' }
    if ($value -match '(?:^|[\\/])(?:cmd)(?:\.exe)?$') { return 'cmd' }
    if ($value -match '(?:^|[\\/])(?:bash|python3?|openclaw)(?:\.exe)?$') { return 'host-process' }
    return 'other'
}

function Get-VisibleLabel([string]$name) {
    if ($name -match '(?i)^(?:bob|openclaw|moltbook)[a-z0-9 ._-]{0,70}$') {
        return $name
    }
    return 'matched-entry-name-withheld'
}

function Get-TriggerCategory([object]$trigger) {
    $className = [string]$trigger.CimClass.CimClassName
    if ($className -match 'Logon') { return 'logon' }
    if ($className -match 'Boot') { return 'boot' }
    if ($className -match 'Time|Daily|Weekly|Monthly|Calendar') { return 'schedule' }
    if ($className -match 'Event') { return 'event' }
    if ($className -match 'Session') { return 'session' }
    return 'other'
}

try {
    $tasks = @(Get-ScheduledTask -ErrorAction Stop)
    foreach ($task in $tasks) {
        $actions = @($task.Actions)
        $matchingActions = @($actions | Where-Object {
            (($PSItem.Execute + ' ' + $PSItem.Arguments + ' ' + $PSItem.WorkingDirectory) -match $markers)
        })
        if ($matchingActions.Count -eq 0 -and ($task.TaskName -notmatch $markers)) { continue }
        $categories = @($matchingActions | ForEach-Object { Get-CommandCategory ([string]$_.Execute) } |
            Sort-Object -Unique)
        $triggers = @($task.Triggers | ForEach-Object { Get-TriggerCategory $_ } | Sort-Object -Unique)
        $matched.Add([pscustomobject]@{
            source = 'scheduled-task'
            label = (Get-VisibleLabel ([string]$task.TaskName))
            state = if ([string]$task.State -in @('Ready', 'Disabled', 'Running')) { [string]$task.State } else { 'other' }
            action_categories = @($categories)
            trigger_categories = @($triggers)
            action_count = $actions.Count
        })
    }
} catch {
    $warnings.Add('scheduled-task-query-unavailable')
}

$registryPaths = @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run'
)
foreach ($key in $registryPaths) {
    try {
        if (-not (Test-Path -LiteralPath $key)) { continue }
        $properties = (Get-ItemProperty -LiteralPath $key).PSObject.Properties
        foreach ($property in $properties) {
            if ($property.Name -match '^PS(?:Path|ParentPath|ChildName|Drive|Provider)$') { continue }
            if (($property.Name + ' ' + [string]$property.Value) -notmatch $markers) { continue }
            $matched.Add([pscustomobject]@{
                source = 'run-registry'
                scope = if ($key.StartsWith('HKCU:')) { 'user' } else { 'machine' }
                label = (Get-VisibleLabel ([string]$property.Name))
            })
        }
    } catch {
        $warnings.Add('run-registry-query-unavailable')
    }
}

$startFolders = @(
    @{ scope = 'user'; path = [Environment]::GetFolderPath('Startup') },
    @{ scope = 'machine'; path = [Environment]::GetFolderPath('CommonStartup') }
)
foreach ($folder in $startFolders) {
    try {
        if (-not $folder.path -or -not (Test-Path -LiteralPath $folder.path)) { continue }
        foreach ($file in @(Get-ChildItem -LiteralPath $folder.path -File -ErrorAction Stop)) {
            if ($file.Name -notmatch $markers) { continue }
            $matched.Add([pscustomobject]@{
                source = 'startup-folder'
                scope = $folder.scope
                label = (Get-VisibleLabel ([string]$file.BaseName))
                extension = if ($file.Extension -in @('.lnk', '.exe', '.cmd', '.bat', '.ps1')) {
                    $file.Extension
                } else { 'other' }
            })
        }
    } catch {
        $warnings.Add('startup-folder-query-unavailable')
    }
}

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    throw 'No user-local output directory is available.'
}
[IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$output = Join-Path $OutputDirectory ("windows-startup-$stamp.json")
if (Test-Path -LiteralPath $output) { throw 'Refusing to overwrite existing report.' }
$report = [ordered]@{
    report_version = 1
    purpose = 'PRIVATE read-only Windows startup discovery; not a reboot recovery proof'
    created_utc = [DateTime]::UtcNow.ToString('o')
    scheduled_task_matches = @($matched | Where-Object source -eq 'scheduled-task').Count
    run_registry_matches = @($matched | Where-Object source -eq 'run-registry').Count
    startup_folder_matches = @($matched | Where-Object source -eq 'startup-folder').Count
    entries = @($matched.ToArray())
    query_warnings = @($warnings.ToArray() | Sort-Object -Unique)
    limitations = @(
        'Only relevant-looking scheduled tasks, Run keys and startup-folder filenames inspected',
        'Action argument values, full paths, environment and registry values were NOT captured',
        'Startup entries using unrelated names or indirect wrappers can be missed',
        'Absence of a match is NOT proof of no reboot recovery',
        'Report is private and must not be pushed to GitHub'
    )
}
$payload = $report | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText($output, $payload, [Text.UTF8Encoding]::new($false))
Write-Output "Private Windows startup report: $output"
Write-Output ("Relevant scheduled tasks: " + $report.scheduled_task_matches)
Write-Output ("Relevant Run entries: " + $report.run_registry_matches)
Write-Output ("Relevant startup-folder items: " + $report.startup_folder_matches)
Write-Output ("Read-only query warnings: " + $report.query_warnings.Count)
Write-Output 'No command arguments, credentials or registry values printed or saved.'
Write-Output 'Windows tasks, startup settings and WSL were NOT changed.'
