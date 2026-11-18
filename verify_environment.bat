@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found. Run environment_setup.bat first.
    exit /b 1
)

call ".venv\Scripts\activate.bat"

python --version
where python
python -c "import sys; assert sys.version_info[:2]==(3,12), 'Expected Python 3.12'; print('Interpreter: PASS')"
if errorlevel 1 exit /b 1

python -c "import fastapi,pydantic,pydantic_settings,sqlalchemy,aiosqlite,httpx,openai,sklearn,pypdf,numpy,scipy; print('Core imports: PASS')"
if errorlevel 1 exit /b 1

python -m pip check
if errorlevel 1 exit /b 1

python -m pytest --version
ruff --version
mypy --version

echo ENVIRONMENT VERIFICATION: PASS
pause
