@echo off
:: start_orchestrator.bat — Launch the Silver Tier Orchestrator
:: The orchestrator watches /Approved and manages watcher processes
::
:: Usage:
::   scripts\start_orchestrator.bat
::
:: The orchestrator will:
::   - Watch /Approved for human-approved items
::   - Route emails to Gmail SMTP sender
::   - Route LinkedIn posts to LinkedIn poster
::   - Restart crashed watcher processes

setlocal

set "VAULT_PATH=%~dp0.."
cd /d "%VAULT_PATH%"

echo ============================================
echo  AI Employee — Starting Orchestrator
echo  Vault: %VAULT_PATH%
echo ============================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH.
    pause
    exit /b 1
)

if not exist "orchestrator.py" (
    echo ERROR: orchestrator.py not found in %VAULT_PATH%
    pause
    exit /b 1
)

if not exist ".env" (
    echo WARNING: .env not found — running in DRY_RUN mode
    set "DRY_RUN=true"
)

echo Starting orchestrator (manages all watchers + approved actions)...
echo Press Ctrl+C to stop.
echo.

python orchestrator.py --vault "%VAULT_PATH%"
