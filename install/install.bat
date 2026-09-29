@echo off
setlocal
cd /d "%~dp0"

REM Other PC: Python lives in this folder (python.exe inside it).
if exist "E:\ishtapython\python.exe" (
  set "ACCRUE_PYTHON=E:\ishtapython\python.exe"
  echo Using Python: E:\ishtapython\python.exe
) else if exist "E:\ishtapython" (
  set "ACCRUE_PYTHON=E:\ishtapython"
  echo Using Python folder: E:\ishtapython
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
  echo.
  echo Install failed. Read the messages above, then see docs\INSTALLATION_GUIDE.md
  pause
  exit /b 1
)
echo.
pause
