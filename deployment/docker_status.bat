@echo off
setlocal

echo ================================================
echo MQI Docker Status
echo ================================================
echo.

docker compose ps

echo.
echo ================================================
echo API HEALTH
echo ================================================
echo.

curl http://localhost:8000/health

echo.
echo.

echo ================================================
echo API READINESS
echo ================================================
echo.

curl http://localhost:8000/readiness

echo.