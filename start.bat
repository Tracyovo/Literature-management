@echo off
setlocal

cd /d "%~dp0"

echo Starting backend...
cd Backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
