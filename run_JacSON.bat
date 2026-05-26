@echo off
cd /d "%~dp0"
echo Running JacSON scraper...
python scripts\scraper_runner.py
pause
