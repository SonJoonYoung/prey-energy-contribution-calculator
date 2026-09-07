@echo off
setlocal
cd /d "%~dp0"
title Prey Energy Contribution Calculator

where py >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python was not found.
    echo Install Python 3.13 64-bit, then run this file again.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo =====================================================
    echo First run: preparing the local Python environment...
    echo This is required only once.
    echo =====================================================
    py -m venv .venv
    if errorlevel 1 goto :fail

    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    if errorlevel 1 goto :fail

    pip install -r requirements.txt
    if errorlevel 1 goto :fail
)

echo.
echo Starting Prey Energy Contribution Calculator...
echo Keep this black window open while using the program.
echo.

".venv\Scripts\python.exe" -m streamlit run app.py ^
    --server.address=127.0.0.1 ^
    --server.port=8501 ^
    --server.fileWatcherType=none ^
    --browser.gatherUsageStats=false

goto :end

:fail
echo.
echo Setup failed. Check the error message above.
pause

:end
endlocal
