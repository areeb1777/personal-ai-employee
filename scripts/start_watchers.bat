@echo off
:: start_watchers.bat — Launch all AI Employee watchers in separate windows
:: Run this from the AI_Employee_Vault directory
::
:: Usage:
::   scripts\start_watchers.bat
::
:: To stop all watchers: close the console windows or run scripts\stop_watchers.bat

setlocal

:: Determine vault path (parent of this scripts folder)
set "VAULT_PATH=%~dp0.."
cd /d "%VAULT_PATH%"

echo ============================================
echo  AI Employee — Starting Silver Tier Watchers
echo  Vault: %VAULT_PATH%
echo ============================================
echo.

:: Check Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH.
    echo Install Python 3.13+ from python.org
    pause
    exit /b 1
)

:: Check .env exists
if not exist ".env" (
    echo WARNING: .env file not found.
    echo Copy .env.example to .env and fill in your credentials.
    echo Running in DRY_RUN mode only.
    set "DRY_RUN=true"
)

echo [1/3] Starting File System Watcher...
start "AI-Watcher: FileSystem" cmd /k "python watchers\filesystem_watcher.py --vault "%VAULT_PATH%""

timeout /t 2 /nobreak >nul

echo [2/3] Starting Gmail Watcher...
start "AI-Watcher: Gmail" cmd /k "python watchers\gmail_watcher.py --vault "%VAULT_PATH%""

timeout /t 2 /nobreak >nul

echo [3/3] Starting LinkedIn Watcher...
start "AI-Watcher: LinkedIn" cmd /k "python watchers\linkedin_watcher.py --vault "%VAULT_PATH%""

timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo  All 3 watchers started in separate windows.
echo  To stop: close the watcher console windows
echo  To view logs: check Logs\{today}.json
echo ============================================
echo.
echo Press any key to close this launcher...
pause >nul
