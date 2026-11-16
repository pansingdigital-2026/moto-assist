@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.12 64-bit from python.org, including the Python Launcher, then retry.
  pause
  exit /b 1
)
py -3.12 -c "import struct; assert struct.calcsize('P') == 8, '64-bit Python required'"
if errorlevel 1 exit /b 1
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -e ".[dev]"
if errorlevel 1 (
  echo Setup failed. Check the error above and docs\TROUBLESHOOTING.md.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip check
if errorlevel 1 exit /b 1
echo Setup complete. Run run.bat --simulate first, then run.bat for Windows hardware.
pause
