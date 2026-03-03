# setup_task_scheduler.ps1 — Windows Task Scheduler setup for Silver Tier
#
# Creates three scheduled tasks:
#   1. AI-Employee-Orchestrator  — Starts orchestrator.py on login (always-on)
#   2. AI-Employee-Weekly-Brief  — Monday 7:00 AM: generate weekly CEO briefing
#   3. AI-Employee-Daily-Triage  — Daily 8:00 AM: run triage-needs-action cycle
#
# Usage (run as Administrator):
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#   .\scripts\setup_task_scheduler.ps1 -VaultPath "C:\path\to\AI_Employee_Vault"
#
# Requirements: Python in PATH, vault .env configured

param(
    [Parameter(Mandatory=$true)]
    [string]$VaultPath,

    [string]$PythonPath = "python",

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "=== AI Employee — Task Scheduler Setup ===" -ForegroundColor Cyan
Write-Host "Vault: $VaultPath"
Write-Host "Python: $PythonPath"
if ($DryRun) { Write-Host "DRY RUN — tasks will not be created" -ForegroundColor Yellow }

# Validate vault path
if (-not (Test-Path $VaultPath)) {
    Write-Error "Vault path not found: $VaultPath"
    exit 1
}

$OrchestratorScript = Join-Path $VaultPath "orchestrator.py"
if (-not (Test-Path $OrchestratorScript)) {
    Write-Error "orchestrator.py not found in vault: $OrchestratorScript"
    exit 1
}

# ---------------------------------------------------------------------------
# Task 1: Orchestrator — start on user login, keep running
# ---------------------------------------------------------------------------
$Task1Name = "AI-Employee-Orchestrator"
$Task1Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$OrchestratorScript`" --vault `"$VaultPath`" --no-watchers" `
    -WorkingDirectory $VaultPath

$Task1Trigger = New-ScheduledTaskTrigger -AtLogOn
$Task1Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

Write-Host "`n[1] Registering: $Task1Name"
if (-not $DryRun) {
    Register-ScheduledTask `
        -TaskName $Task1Name `
        -Action $Task1Action `
        -Trigger $Task1Trigger `
        -Settings $Task1Settings `
        -RunLevel Highest `
        -Force | Out-Null
    Write-Host "    ✅ Created: starts on login, restarts on failure" -ForegroundColor Green
} else {
    Write-Host "    [DRY RUN] Would create task: $Task1Name" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Task 2: Weekly CEO Briefing — Every Monday at 7:00 AM
# ---------------------------------------------------------------------------
$Task2Name = "AI-Employee-Weekly-Briefing"
$ClaudeCmd = "claude"
$BriefingPrompt = "/generate-weekly-briefing"

$Task2Action = New-ScheduledTaskAction `
    -Execute $ClaudeCmd `
    -Argument "--print `"$BriefingPrompt`"" `
    -WorkingDirectory $VaultPath

$Task2Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "07:00"

Write-Host "`n[2] Registering: $Task2Name"
if (-not $DryRun) {
    Register-ScheduledTask `
        -TaskName $Task2Name `
        -Action $Task2Action `
        -Trigger $Task2Trigger `
        -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 30)) `
        -RunLevel Highest `
        -Force | Out-Null
    Write-Host "    ✅ Created: Every Monday at 7:00 AM" -ForegroundColor Green
} else {
    Write-Host "    [DRY RUN] Would create task: $Task2Name (Monday 7:00 AM)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Task 3: Daily Triage — Every day at 8:00 AM
# ---------------------------------------------------------------------------
$Task3Name = "AI-Employee-Daily-Triage"
$TriagePrompt = "/triage-needs-action"

$Task3Action = New-ScheduledTaskAction `
    -Execute $ClaudeCmd `
    -Argument "--print `"$TriagePrompt`"" `
    -WorkingDirectory $VaultPath

$Task3Trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

Write-Host "`n[3] Registering: $Task3Name"
if (-not $DryRun) {
    Register-ScheduledTask `
        -TaskName $Task3Name `
        -Action $Task3Action `
        -Trigger $Task3Trigger `
        -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 15)) `
        -RunLevel Highest `
        -Force | Out-Null
    Write-Host "    ✅ Created: Every day at 8:00 AM" -ForegroundColor Green
} else {
    Write-Host "    [DRY RUN] Would create task: $Task3Name (Daily 8:00 AM)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Task 4: LinkedIn Auto-Post — Weekdays at 9:00 AM
# ---------------------------------------------------------------------------
$Task4Name = "AI-Employee-LinkedIn-Post"
$LinkedInPrompt = "/draft-linkedin-post"

$Task4Action = New-ScheduledTaskAction `
    -Execute $ClaudeCmd `
    -Argument "--print `"$LinkedInPrompt`"" `
    -WorkingDirectory $VaultPath

# Run Mon-Fri at 9:00 AM
$Task4Trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "09:00"

Write-Host "`n[4] Registering: $Task4Name"
if (-not $DryRun) {
    Register-ScheduledTask `
        -TaskName $Task4Name `
        -Action $Task4Action `
        -Trigger $Task4Trigger `
        -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10)) `
        -RunLevel Highest `
        -Force | Out-Null
    Write-Host "    ✅ Created: Weekdays at 9:00 AM" -ForegroundColor Green
} else {
    Write-Host "    [DRY RUN] Would create task: $Task4Name (Mon-Fri 9:00 AM)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Tasks created:" -ForegroundColor White
Write-Host "  $Task1Name    — On login, auto-restart" -ForegroundColor Gray
Write-Host "  $Task2Name — Monday 7:00 AM" -ForegroundColor Gray
Write-Host "  $Task3Name       — Daily 8:00 AM" -ForegroundColor Gray
Write-Host "  $Task4Name     — Weekdays 9:00 AM" -ForegroundColor Gray
Write-Host "`nVerify in Task Scheduler (taskschd.msc)" -ForegroundColor White
Write-Host "Or run: Get-ScheduledTask | Where-Object { `$_.TaskName -like 'AI-Employee-*' }"
