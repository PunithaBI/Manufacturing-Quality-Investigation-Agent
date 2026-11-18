@echo off
setlocal

echo ================================================
echo Stopping MQI Docker Services
echo ================================================
echo.

docker compose down

if errorlevel 1 (
    echo.
    echo DOCKER SHUTDOWN FAILED
    exit /b 1
)

echo.
echo Docker services stopped.

exit /b 0