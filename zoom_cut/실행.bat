@echo off
chcp 65001 > nul
cd /d "%~dp0"
python zoom_cut.py %1
echo.
pause
