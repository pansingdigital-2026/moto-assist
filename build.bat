@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name MotoAssist --collect-all dxcam --collect-all sdl2 --collect-all sdl2dll --collect-all rapidocr_onnxruntime --collect-all onnxruntime --hidden-import comtypes scripts\launch.py
set "MOTOASSIST_RESULT=%ERRORLEVEL%"
if not "%MOTOASSIST_RESULT%"=="0" pause
exit /b %MOTOASSIST_RESULT%
