@echo off
setlocal
cd /d "%~dp0"

call environment_setup.bat
if errorlevel 1 exit /b 1

call verify_environment.bat
if errorlevel 1 exit /b 1

call create_lock.bat
if errorlevel 1 exit /b 1

echo.
echo FULL ENVIRONMENT SETUP: PASS
pause
