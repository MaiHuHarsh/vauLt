@echo off
cd /d %~dp0

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
echo Installing dependencies (first run only takes a minute)...
pip install -q -r requirements.txt

echo.
echo Starting backend on http://localhost:8000 ...
start "Secure DMS Backend" cmd /k uvicorn app.main:app --host 0.0.0.0 --port 8000

timeout /t 4 /nobreak >nul

echo Starting frontend on http://localhost:8501 ...
cd frontend
streamlit run app.py --server.port 8501
