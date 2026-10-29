@echo off
:: ============================================================
:: AYUSH AI Launcher (CLI Primary Interface)
:: ============================================================

setlocal
cd /d "%~dp0"

:: Activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Run the primary CLI agent
python ayush.py %*
endlocal
