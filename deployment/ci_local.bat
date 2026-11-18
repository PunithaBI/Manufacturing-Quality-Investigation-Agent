@echo off
setlocal

echo ================================================
echo MQI LOCAL CI CHECK
echo ================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo [1/5] Compile Python sources
%PYTHON% -m compileall app deployment evaluation

if errorlevel 1 (
    echo.
    echo COMPILE FAILED
    exit /b 1
)

echo.
echo [2/5] Ruff lint
%PYTHON% -m ruff check app deployment evaluation

if errorlevel 1 (
    echo.
    echo LINT FAILED
    exit /b 1
)

echo.
echo [3/5] Security checks
%PYTHON% -m pytest tests/security -q

if errorlevel 1 (
    echo.
    echo SECURITY CHECKS FAILED
    exit /b 1
)

echo.
echo [4/5] Evaluation
%PYTHON% -m evaluation.run_evaluation

if errorlevel 1 (
    echo.
    echo EVALUATION FAILED
    exit /b 1
)

echo.
echo [5/5] Docker build
docker build -t manufacturing-quality-investigation-agent:ci .

if errorlevel 1 (
    echo.
    echo DOCKER BUILD FAILED
    exit /b 1
)

echo.
echo ================================================
echo MQI LOCAL CI PASS
echo ================================================

exit /b 0