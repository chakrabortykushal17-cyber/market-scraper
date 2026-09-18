@echo off
title Enable PC Auto-Start — Finance Intel Scraper
echo ========================================================
echo   Enabling PC Auto-Start for Market Data Scraper...
echo ========================================================
python "%~dp0autostart.py" --enable --target scraper
echo.
pause
