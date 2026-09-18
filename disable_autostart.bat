@echo off
title Disable PC Auto-Start — Finance Intel Scraper
echo ========================================================
echo   Disabling PC Auto-Start for Market Data Scraper...
echo ========================================================
python "%~dp0autostart.py" --disable
echo.
pause
