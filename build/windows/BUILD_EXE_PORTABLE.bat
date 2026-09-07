@echo off
setlocal
cd /d "%~dp0\..\.."
title Build Prey Energy Calculator - Portable EXE

echo ============================================================
echo Prey Energy Contribution Calculator - Windows EXE Builder
echo ============================================================
echo.
echo Recommended build: portable folder with EXE.
echo The finished folder can run on a Windows PC without Python.
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo Python was not found.
    echo Install Python 3.13 64-bit and try again.
    pause
    exit /b 1
)

if not exist ".buildvenv\Scripts\python.exe" (
    echo Creating build environment...
    py -m venv .buildvenv
    if errorlevel 1 goto :fail
)

call ".buildvenv\Scripts\activate.bat"

echo Installing/updating build packages...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
pip install --upgrade -r build\windows\build_requirements.txt
if errorlevel 1 goto :fail

echo.
echo Running PECC data and fallback self-test...
python self_test.py
if errorlevel 1 goto :fail

echo.
echo Cleaning previous build...
if exist .pyinstaller_build rmdir /s /q .pyinstaller_build
if exist dist rmdir /s /q dist
if exist PreyEnergyCalculator.spec del /q PreyEnergyCalculator.spec

echo.
echo Building portable EXE...
pyinstaller --noconfirm --clean --onedir --console ^
  --workpath .pyinstaller_build ^
  --name PreyEnergyCalculator ^
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
echo ============================================================
echo BUILD COMPLETE
echo ============================================================
echo.
echo Run:
echo dist\PreyEnergyCalculator\PreyEnergyCalculator.exe
echo.
echo IMPORTANT:
echo Copy the ENTIRE "dist\PreyEnergyCalculator" folder if you
echo want to use the program on another Windows PC.
echo.
explorer "dist\PreyEnergyCalculator"
pause
exit /b 0

:fail
echo.
echo BUILD FAILED.
echo Keep this window open and send a screenshot of the error.
pause
exit /b 1
