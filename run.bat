@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m motoassist %*
set "MOTOASSIST_RESULT=%ERRORLEVEL%"
if not "%MOTOASSIST_RESULT%"=="0" pause
exit /b %MOTOASSIST_RESULT%
