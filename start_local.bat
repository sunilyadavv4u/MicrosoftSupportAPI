@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  py -3.11 -m venv .venv
  if errorlevel 1 exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist ".env" copy ".env.example" ".env"
if not exist "data\mock_api.db" python scripts\load_data.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
