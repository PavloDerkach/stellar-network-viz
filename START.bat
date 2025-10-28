@echo off
echo ========================================
echo  Stellar Network Visualization
echo  Starting application...
echo ========================================
echo.

REM Активация виртуального окружения (если есть)
if exist venv\Scripts\activate.bat (
    echo [1/2] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [!] No virtual environment found, using global Python
)

echo [2/2] Starting Streamlit app...
echo.
echo ----------------------------------------
echo  App will open at: http://localhost:8501
echo  Press Ctrl+C to stop
echo ----------------------------------------
echo.

streamlit run web\app.py

pause
