@echo off
setlocal

cd /d "%~dp0"

start "Literature Manager API" cmd /c start.bat
start "Literature Manager UI" "Frontend\index.html"

endlocal
