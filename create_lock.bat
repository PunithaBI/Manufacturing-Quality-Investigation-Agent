@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found. Run environment_setup.bat first.
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m pip freeze > requirements.lock
if errorlevel 1 exit /b 1

echo requirements.lock created from the verified environment.
pause
