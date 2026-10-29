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

function Get-WrapperClassification([string]$target, [string]$arguments) {
    # Classify shortcut-related launcher scripts in memory. Never execute them.
    $info = [ordered]@{
        executable_kind = 'other'
        executable_is_openclaw_named = $false
        wrapper_script = 'not-found'
        script_mentions_wsl = $false
        script_mentions_openclawlab = $false
        script_mentions_systemd = $false
    }
    $base = [IO.Path]::GetFileName($target).ToLowerInvariant()
    if ($base -in @('wt.exe','windowsterminal.exe','windowsterminal')) {
        $info.executable_kind = 'windows-terminal'
    } elseif ($base -in @('wscript.exe','cscript.exe','mshta.exe')) {
        $info.executable_kind = 'script-host'
    } elseif ($base -match '^(?:pythonw?|py)(?:\.exe)?$') {
        $info.executable_kind = 'python'
    } elseif ($base -match '^(?:powershell|pwsh)(?:\.exe)?$') {
        $info.executable_kind = 'powershell'
    } elseif ($base -match '^wsl(?:\.exe)?$') {
        $info.executable_kind = 'wsl'
    } elseif ($base -match '\.(?:ps1|cmd|bat)$') {
        $info.executable_kind = 'script'
    } elseif ($base -match '\.exe$') {
        $info.executable_kind = 'executable'
    }
    $info.executable_is_openclaw_named = ($base -match '(?i)(?:openclaw|moltbook)')
    $candidate = $null
    if ($info.executable_kind -eq 'script') {
        $candidate = $target
    } elseif ($info.executable_kind -eq 'powershell') {
        if ($arguments -match '(?i)(?:^|\s)-File\s+(?:"([^"]+\.ps1)"|''([^'']+\.ps1)''|([^\s"'']+\.ps1))(?=\s|$)') {
            foreach ($part in @($Matches[1], $Matches[2], $Matches[3])) {
                if (-not [string]::IsNullOrWhiteSpace($part)) {
                    $candidate = [string]$part
                    break
                }
            }
        }
    }
    if (-not $candidate) { return [pscustomobject]$info }
    $info.wrapper_script = 'unavailable'
    try {
        $expanded = [Environment]::ExpandEnvironmentVariables($candidate)
        # No UNC shares, network links, relative paths or oversized files.
        if ($expanded -notmatch '^[A-Za-z]:\\') { return [pscustomobject]$info }
        $item = Get-Item -LiteralPath $expanded -ErrorAction Stop
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
            $item.Length -gt 65536 -or $item.Length -le 0 -or
            $item.Extension -notin @('.ps1', '.cmd', '.bat')) {
            return [pscustomobject]$info
        }
        $contents = [IO.File]::ReadAllText($item.FullName)
        $info.wrapper_script = 'inspected'
        $info.script_mentions_wsl = ($contents -match '(?i)(?:^|[^a-z0-9_-])wsl(?:\.exe)?(?:$|[^a-z0-9_-])')
        $info.script_mentions_openclawlab = ($contents -match '(?i)(?:^|[^a-z0-9_-])OpenClawLab(?:$|[^a-z0-9_-])')
        $info.script_mentions_systemd = ($contents -match '(?i)(?:systemctl|systemd)')
    } catch {
        $info.wrapper_script = 'unavailable'
    }
    return [pscustomobject]$info
}

function Get-ShortcutLaunchShape([System.IO.FileInfo]$file) {
    # Inspect a .lnk target and arguments in memory only. NEVER record them.
    $shape = [ordered]@{
        target_category = 'not-inspected'
        target_inspected = $false
        mentions_wsl = $false
        mentions_openclawlab = $false
        executable_kind = 'not-inspected'
        executable_is_openclaw_named = $false
        wrapper_script = 'not-found'
        script_mentions_wsl = $false
        script_mentions_openclawlab = $false
        script_mentions_systemd = $false
    }
    if ($file.Extension -ne '.lnk') {
        return [pscustomobject]$shape
    }
    $shell = $null
    $shortcut = $null
    try {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($file.FullName)
        $target = [string]$shortcut.TargetPath
        $args = [string]$shortcut.Arguments
        $shape.target_category = Get-CommandCategory $target
        $shape.target_inspected = $true
        $shape.mentions_wsl = (($shape.target_category -eq 'wsl') -or
            ($args -match '(?i)(?:^|[^a-z0-9_-])wsl(?:\.exe)?(?:$|[^a-z0-9_-])'))
        $shape.mentions_openclawlab = ($args -match '(?i)(?:^|[^a-z0-9_-])OpenClawLab(?:$|[^a-z0-9_-])')
        $wrapper = Get-WrapperClassification $target $args
        $shape.executable_kind = $wrapper.executable_kind
        $shape.executable_is_openclaw_named = $wrapper.executable_is_openclaw_named
        $shape.wrapper_script = $wrapper.wrapper_script
        $shape.script_mentions_wsl = $wrapper.script_mentions_wsl
        $shape.script_mentions_openclawlab = $wrapper.script_mentions_openclawlab
        $shape.script_mentions_systemd = $wrapper.script_mentions_systemd
    } catch {
        $shape.target_category = 'inspection-unavailable'
        $warnings.Add('shortcut-target-inspection-unavailable')
    } finally {
        if ($null -ne $shortcut) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shortcut) }
        if ($null -ne $shell) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shell) }
    }
    return [pscustomobject]$shape
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
            $shape = Get-ShortcutLaunchShape $file
            $matched.Add([pscustomobject]@{
                source = 'startup-folder'
                scope = $folder.scope
                label = (Get-VisibleLabel ([string]$file.BaseName))
                extension = if ($file.Extension -in @('.lnk', '.exe', '.cmd', '.bat', '.ps1')) {
                    $file.Extension
                } else { 'other' }
                launch_category = $shape.target_category
                shortcut_target_inspected = $shape.target_inspected
                shortcut_mentions_wsl = $shape.mentions_wsl
                shortcut_mentions_openclawlab = $shape.mentions_openclawlab
                executable_kind = $shape.executable_kind
                executable_is_openclaw_named = $shape.executable_is_openclaw_named
                wrapper_script = $shape.wrapper_script
                script_mentions_wsl = $shape.script_mentions_wsl
                script_mentions_openclawlab = $shape.script_mentions_openclawlab
                script_mentions_systemd = $shape.script_mentions_systemd
                trigger_category = 'interactive-logon'
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
        'Matching shortcuts are inspected in memory; small local scripts may be read for WSL/distro/systemd presence indicators',
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
foreach ($entry in @($matched | Where-Object source -eq 'startup-folder')) {
    Write-Output ("Startup item: {0}; scope={1}; extension={2}; target={3}; wsl={4}; distro={5}" -f
        $entry.label, $entry.scope, $entry.extension, $entry.launch_category,
        $entry.shortcut_mentions_wsl, $entry.shortcut_mentions_openclawlab)
    Write-Output ("  launch kind={0}; openclaw-named={1}; wrapper={2}; wrapper-wsl={3}; wrapper-distro={4}; wrapper-systemd={5}" -f
        $entry.executable_kind, $entry.executable_is_openclaw_named,
        $entry.wrapper_script, $entry.script_mentions_wsl,
        $entry.script_mentions_openclawlab, $entry.script_mentions_systemd)
}
Write-Output 'No shortcut targets, wrapper contents, command arguments, executable paths, credentials or registry values printed or saved.'
Write-Output 'Windows tasks, startup settings and WSL were NOT changed.'
