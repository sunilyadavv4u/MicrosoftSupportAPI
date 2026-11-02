@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python scripts\load_data.py --reload
pause
