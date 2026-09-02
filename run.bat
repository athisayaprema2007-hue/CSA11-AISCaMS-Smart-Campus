@echo off
REM ===================================================================
REM  AISCaMS - AI-Enabled Smart Campus Management System
REM  One click setup and start for Windows.
REM ===================================================================
setlocal
cd /d "%~dp0"

echo.
echo  ==========================================================
echo   AISCaMS - AI-Enabled Smart Campus Management System
echo  ==========================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH. Install Python 3.10+ and retry.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/4] Creating the virtual environment ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment already present.
)

echo [2/4] Installing dependencies ...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo [3/4] Creating and seeding the database ...
call ".venv\Scripts\python.exe" manage.py seed
if errorlevel 1 (
    echo [ERROR] Database initialisation failed.
    pause
    exit /b 1
)

echo [4/4] Starting the application on http://127.0.0.1:5000
echo       Demo password for every account: campus123
echo       Press CTRL+C to stop the server.
echo.
start "" "http://127.0.0.1:5000"
call ".venv\Scripts\python.exe" run.py

endlocal
