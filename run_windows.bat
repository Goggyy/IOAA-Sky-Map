@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3.11 -m venv .venv 2>nul
    if errorlevel 1 py -m venv .venv
    if errorlevel 1 goto :error

    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo The trainer could not start. Review the error above.
pause
exit /b 1
