@echo off
echo ========================================
echo  Stellar Network Visualization Launcher
echo ========================================
echo.

REM Get current directory (where this script is located)
set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

echo Current directory: %PROJECT_DIR%
echo.

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
) else (
    echo WARNING: No virtual environment found!
    echo Creating new virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing requirements...
    pip install -r requirements.txt
)

echo.
echo Starting Stellar Network Visualization...
echo ----------------------------------------
echo.

REM Run the Streamlit app
streamlit run web\app.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start the application!
    echo Please check the error message above.
    pause
)
