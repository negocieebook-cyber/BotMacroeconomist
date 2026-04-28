@echo off
setlocal
cd /d "%~dp0"

where npm >nul 2>nul
if %errorlevel%==0 (
  npm.cmd run start
  exit /b %errorlevel%
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" main.py start
  exit /b %errorlevel%
)

python main.py start
