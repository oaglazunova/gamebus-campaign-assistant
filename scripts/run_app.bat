@echo off
setlocal

echo.
echo ============================================
echo   GameBus Campaign Assistant - Start
echo ============================================
echo.

REM Move to repo root (script is inside /scripts)
cd /d "%~dp0\.."

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: The app is not installed yet.
    echo.
    echo Please run:
    echo   scripts\install_windows.bat
    echo.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo Starting GameBus Campaign Assistant...
echo.
echo If your browser does not open automatically,
echo please copy the local URL shown below into your browser.
echo.

streamlit run src/campaign_assistant/app.py

if errorlevel 1 (
    echo.
    echo ERROR: The app did not start correctly.
    echo.
    echo Please check that installation completed successfully.
    echo If needed, run:
    echo   scripts\install_windows.bat
    echo.
    pause
    exit /b 1
)

endlocal
exit /b 0