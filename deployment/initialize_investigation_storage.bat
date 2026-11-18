@echo off
setlocal

echo ================================================
echo Manufacturing Quality Investigation Agent
echo Persistent Storage Initialization
echo ================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv was not found.
    echo Activate/create the project environment first.
    exit /b 1
)

echo Using project Python...
echo.

.venv\Scripts\python.exe deployment\initialize_investigation_storage.py

if errorlevel 1 (
    echo.
    echo STORAGE INITIALIZATION FAILED
    exit /b 1
)

echo.
echo ================================================
echo STORAGE INITIALIZATION COMPLETE
echo ================================================
echo.

exit /b 0