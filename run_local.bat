@echo off
REM Script chay SbayAI o local (Windows CMD)
cd /d "%~dp0"

if not exist "venv" (
    echo =^> Tao virtualenv...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo =^> Cai dependencies...
pip install -q -r requirements.txt

if not exist ".env" (
    echo =^> Chua co .env - copy tu .env.example
    copy .env.example .env
    echo !!! Hay mo file .env va dien DEEPSEEK_API_KEY truoc khi chay lai
    pause
    exit /b 1
)

echo =^> Khoi dong server tai http://localhost:8080
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8080
