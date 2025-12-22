@echo off
echo Starting ROC City Pickleball Ladder League Configurator...
echo.

python ladder_league.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start application
    echo.
    echo Possible issues:
    echo   1. Python not installed
    echo   2. PyQt6 not installed - run: pip install -r requirements.txt
    echo.
    pause
)
