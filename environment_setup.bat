@echo off
setlocal
cd /d "%~dp0"

echo === Manufacturing Quality Investigation Agent Setup ===

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.12 not found.
    echo Install Python 3.12 x64 from https://www.python.org/downloads/
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 exit /b 1

call ".venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1

python -c "import sys; assert sys.version_info[:2]==(3,12), sys.version; print('Python 3.12 OK')"
if errorlevel 1 exit /b 1

python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

python -m pip install -r requirements-dev.txt
if errorlevel 1 exit /b 1

python -c "import fastapi,pydantic,pydantic_settings,sqlalchemy,aiosqlite,httpx,openai,sklearn,pypdf,numpy,scipy; print('Core imports: PASS')"
if errorlevel 1 exit /b 1

python -m pip check
if errorlevel 1 exit /b 1

python -m pip install "sentence-transformers>=5.1,<6" "numpy>=2.0,<3"
if errorlevel 1 exit /b 1

echo SETUP COMPLETE
pause
