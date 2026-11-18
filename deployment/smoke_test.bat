@echo off
setlocal

echo ================================================
echo MQI Docker Production Smoke Test
echo ================================================
echo.

echo Checking Docker containers...
docker compose ps

if errorlevel 1 (
    echo.
    echo ERROR: Docker Compose is not available.
    exit /b 1
)

echo.
echo Running HTTP smoke tests...
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe deployment\smoke_test.py
) else (
    python deployment\smoke_test.py
)

if errorlevel 1 (
    echo.
    echo ================================================
    echo SMOKE TEST FAILED
    echo ================================================
    exit /b 1
)

echo.
echo ================================================
echo SMOKE TEST PASS
echo ================================================

exit /b 0