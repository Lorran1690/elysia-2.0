@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Ambiente Python nao encontrado. Consulte interface\DESKTOP.md.
  pause
  exit /b 1
)
start "Elysia" ".venv\Scripts\pythonw.exe" -m interface.desktop
