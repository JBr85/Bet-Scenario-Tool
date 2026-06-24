@echo off
setlocal

REM Project folder = wherever this .bat lives (works on any machine)
set "PROJECT=%~dp0"
cd /d "%PROJECT%"

REM Machine-local venv stored outside OneDrive — each PC manages its own copy
set "VENV=%USERPROFILE%\.bet_scenario_tool_venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo ============================================
    echo  First-time setup on this machine...
    echo ============================================
    where python >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  ERROR: Python not found on this machine.
        echo  Install Python 3.9+ from https://python.org
        echo  Tick "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
    echo Creating virtual environment...
    python -m venv "%VENV%"
    echo.
)

echo Checking packages...
"%VENV%\Scripts\pip" install -q -r "%PROJECT%requirements.txt"

echo Starting Bet Scenario Tool...
REM Use python.exe (with console) so Flask's debug auto-reloader works.
REM pythonw.exe (windowless) breaks reloader because the subprocess restart has no console handle.
start "Bet Scenario Tool" "%VENV%\Scripts\python.exe" "%PROJECT%app.py"

timeout /t 2 /nobreak >nul
start http://localhost:5000
