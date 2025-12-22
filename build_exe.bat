@echo off
echo ========================================
echo ROC City Pickleball - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Python found!
echo.

REM Check if PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing dependencies...
    python -m pip install -r requirements.txt
    echo.
)

echo Building executable...
echo This may take a few minutes...
echo.

python -m PyInstaller --onefile --windowed --name "ROC_City_Ladder_League" --add-data "RocCityPickleball_4k.png;." ladder_league.py --clean

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo Your executable is located at:
    echo   dist\ROC_City_Ladder_League.exe
    echo.
    echo IMPORTANT: Copy these files to the club PC:
    echo   1. dist\ROC_City_Ladder_League.exe
    echo   2. RocCityPickleball_4k.png
    echo.
    echo Place them in the same folder and run the .exe
    echo.
) else (
    echo.
    echo ========================================
    echo BUILD FAILED!
    echo ========================================
    echo Please check the error messages above.
    echo.
)

pause
