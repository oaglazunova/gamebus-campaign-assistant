@echo off
setlocal

echo.
echo ============================================
echo   GameBus Campaign Assistant - Installation
echo ============================================
echo.

REM Move to repo root (script is inside /scripts)
cd /d "%~dp0\.."

echo [1/5] Checking Python 3.14...
py -3.14 --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Python 3.14 is not installed or not available.
    echo Please install Python 3.14 and make sure it is available via the Python launcher.
    echo.
    pause
    exit /b 1
)

echo [2/5] Removing old virtual environment...
if exist ".venv" (
    rmdir /s /q ".venv"
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to remove existing virtual environment.
        echo Please close terminals/editors using .venv and try again.
        echo.
        pause
        exit /b 1
    )
)

echo [3/5] Creating virtual environment with Python 3.14...
py -3.14 -m venv .venv
if errorlevel 1 (
    echo.
    echo ERROR: Failed to create virtual environment.
    echo.
    pause
    exit /b 1
)

echo [4/5] Upgrading pip...
call ".venv\Scripts\activate.bat"

python -m ensurepip --upgrade
if errorlevel 1 (
    echo.
    echo ERROR: Failed to bootstrap pip.
    echo.
    pause
    exit /b 1
)

python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo.
    echo ERROR: Failed to upgrade pip.
    echo.
    pause
    exit /b 1
)

echo [5/5] Installing GameBus Campaign Assistant...
python -m pip install -e ".[dev]"
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install the project.
    echo.
    echo If this happened during package download, please check:
    echo - your internet connection
    echo - whether Python package downloads are allowed on this network
    echo - whether the project defines a [dev] extra in pyproject.toml
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
echo.
echo For tests, run:
echo   pytest
echo ============================================
echo.
pause
exit /b 0