@echo off
:: start_all.bat — Start all AI Employee processes
:: Double-click this file to start everything

cd /d "%~dp0.."
set VAULT=%~dp0..

echo ============================================
echo  AI Employee — Starting All Services
echo ============================================

:: Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [WARN] No .venv found — using system Python
)

echo.
echo Starting services in separate windows...
echo.

:: Start Gmail Watcher
start "Gmail Watcher" cmd /k "cd /d "%VAULT%" && call .venv\Scripts\activate.bat && python watchers/gmail_watcher.py"

:: Start LinkedIn Watcher
start "LinkedIn Watcher" cmd /k "cd /d "%VAULT%" && call .venv\Scripts\activate.bat && python watchers/linkedin_watcher.py"

:: Start Filesystem Watcher
start "File Watcher" cmd /k "cd /d "%VAULT%" && call .venv\Scripts\activate.bat && python watchers/filesystem_watcher.py"

:: Start Orchestrator (no-watchers since we started them above)
start "Orchestrator" cmd /k "cd /d "%VAULT%" && call .venv\Scripts\activate.bat && python orchestrator.py --no-watchers"

echo [OK] All services started in separate windows
echo.
echo To stop: close each window individually
echo.
pause
