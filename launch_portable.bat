@echo off
setlocal

cd /d "%~dp0"

start "Literature Manager API" "%~dp0LiteratureManagerBackend.exe"

timeout /t 2 >nul

start "Literature Manager UI" "%~dp0Frontend\index.html"

endlocal
