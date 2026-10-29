@echo off
echo ===================================================
echo Setting up Ayush AI Environment
echo ===================================================

:: Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found on PATH. Please install Python 3.11 and try again.
    pause
    exit /b 1
)

echo [OK] Python found.

:: Create virtual environment if not present
if not exist ".venv" (
    echo Creating virtual environment in .venv...
    python -m venv .venv
)

:: Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

:: Upgrade pip and install requirements
echo Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: Ensure Playwright Chromium browser is installed
echo Ensuring Playwright browser binaries are ready...
python -m playwright install chromium

echo ===================================================
echo Ayush AI setup completed successfully!
echo To run the application, execute: run.bat
echo ===================================================
pause
