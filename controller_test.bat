@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m motoassist.controller_test %*
set "MOTOASSIST_RESULT=%ERRORLEVEL%"
pause
exit /b %MOTOASSIST_RESULT%
