@echo off
setlocal

cd /d "%~dp0"

set "EXE=%~dp0LiteratureManagerBackend.exe"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if exist "%EXE%" (
	echo Starting backend (exe)...
	"%EXE%"
	goto :eof
)

if exist "%VENV_PY%" (
	echo Starting backend (venv)...
	pushd Backend
	"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
	popd
	goto :eof
)

echo Starting backend (system python)...
pushd Backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
popd
