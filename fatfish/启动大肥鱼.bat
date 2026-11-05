@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 launcher.py
) else (
  python launcher.py
)
if errorlevel 1 (
  echo 请确认已安装 Python 3.10 或更新版本，并勾选 Add Python to PATH。
  pause
)
