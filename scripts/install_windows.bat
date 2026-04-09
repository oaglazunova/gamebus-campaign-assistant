@echo off
setlocal

echo.
echo ============================================
echo   GameBus Campaign Assistant - Installation
echo ============================================
echo.

REM Move to repo root (script is inside /scripts)
cd /d "%~dp0\.."

echo [1/4] Checking Python...
python --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not available in PATH.
    echo Please install Python 3.11 or newer and make sure
    echo "Add Python to PATH" is enabled during installation.
    echo.
    pause
    exit /b 1
)

echo [2/4] Creating virtual environment...
if exist ".venv" (
    echo Virtual environment already exists. Reusing it.
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )
)

echo [3/4] Upgrading pip...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo ERROR: Failed to upgrade pip.
    echo.
    pause
    exit /b 1
)

echo [4/4] Installing GameBus Campaign Assistant...
pip install -e .
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install the project.
    echo.
    echo If this happened during package download, please check:
    echo - your internet connection
    echo - whether Python package downloads are allowed on this network
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Installation completed successfully.
echo.
echo Next step:
echo   Double-click scripts\run_app.bat
echo ============================================
echo.
pause
exit /b 0