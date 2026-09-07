@echo off
setlocal
cd /d "%~dp0\..\.."
title Build Prey Energy Calculator - Single EXE

echo ============================================================
echo Prey Energy Contribution Calculator - Single EXE Builder
echo ============================================================
echo.
echo This build creates one EXE file, but it is larger and can
echo start more slowly than the portable-folder build.
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo Python was not found.
    pause
    exit /b 1
)

if not exist ".buildvenv\Scripts\python.exe" (
    py -m venv .buildvenv
    if errorlevel 1 goto :fail
)

call ".buildvenv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
pip install --upgrade -r build\windows\build_requirements.txt
if errorlevel 1 goto :fail

if exist build_onefile rmdir /s /q build_onefile
if exist dist_onefile rmdir /s /q dist_onefile

pyinstaller --noconfirm --clean --onefile --console ^
  --name PreyEnergyCalculator ^
  --distpath dist_onefile ^
  --workpath build_onefile ^
  --add-data "app.py;." ^
  --add-data "data\prey_energy_db_v1_0_0.xlsx;data" ^
  --add-data "validation\validation_reference.json;validation" ^
  --collect-all streamlit ^
  --recursive-copy-metadata streamlit ^
  --collect-all pyarrow ^
  --copy-metadata pyarrow ^
  --collect-data altair ^
  --copy-metadata altair ^
  --collect-data certifi ^
  --copy-metadata pandas ^
  --copy-metadata openpyxl ^
  --copy-metadata requests ^
  --hidden-import streamlit.web.cli ^
  launcher.py

if errorlevel 1 goto :fail

echo.
echo BUILD COMPLETE:
echo dist_onefile\PreyEnergyCalculator.exe
echo.
explorer "dist_onefile"
pause
exit /b 0

:fail
echo.
echo BUILD FAILED.
echo Keep this window open and send a screenshot of the error.
pause
exit /b 1
