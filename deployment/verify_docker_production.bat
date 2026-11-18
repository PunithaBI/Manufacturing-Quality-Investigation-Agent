@echo off
setlocal

echo ================================================
echo MQI Docker Production Verification
echo ================================================
echo.

echo [1/5] Docker version
docker --version

if errorlevel 1 (
    echo ERROR: Docker is not available.
    exit /b 1
)

echo.
echo [2/5] Docker Compose version
docker compose version

if errorlevel 1 (
    echo ERROR: Docker Compose is not available.
    exit /b 1
)

echo.
echo [3/5] Container status
docker compose ps

echo.
echo [4/5] PostgreSQL container health
docker inspect mqi-postgres --format="{{.State.Health.Status}}"

echo.
echo [5/5] API container health
docker inspect mqi-api --format="{{.State.Health.Status}}"

echo.
echo ================================================
echo HTTP PRODUCTION SMOKE TEST
echo ================================================
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe deployment\smoke_test.py
) else (
    python deployment\smoke_test.py
)

if errorlevel 1 (
    echo.
    echo ================================================
    echo PRODUCTION VERIFICATION FAILED
    echo ================================================
    exit /b 1
)

echo.
echo ================================================
echo PRODUCTION VERIFICATION PASS
echo ================================================

exit /b 0