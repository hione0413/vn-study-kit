@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
  echo Python was not found on this PC.
  pause
  exit /b 1
)
start "" pythonw wordwin.py
