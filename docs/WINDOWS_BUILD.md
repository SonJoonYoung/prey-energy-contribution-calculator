# Windows EXE build

The repository includes two PyInstaller build scripts under `build/windows/`. Run them on Windows from their current location; each script changes to the repository root automatically.

## Recommended portable build

Double-click:

`build\windows\BUILD_EXE_PORTABLE.bat`

The script:

1. creates `.buildvenv` if needed;
2. installs packages from `build/windows/build_requirements.txt`;
3. runs `self_test.py`;
4. builds `dist\PreyEnergyCalculator\PreyEnergyCalculator.exe`.

Copy the entire `dist\PreyEnergyCalculator` directory when moving the portable build to another Windows computer. Python is not required on the destination computer.

## Single-file build

After testing the portable build, optionally run:

`build\windows\BUILD_EXE_SINGLE_FILE.bat`

This produces `dist_onefile\PreyEnergyCalculator.exe`. Single-file startup may be slower because bundled files are unpacked at runtime.

## Browser and runtime behavior

The bundled launcher chooses an available local port, starts Streamlit on `127.0.0.1`, waits until the server is reachable, and then attempts to open Chrome. If Chrome is unavailable, it falls back to the Windows default browser. Startup exceptions are written to `PreyEnergyCalculator_error.txt`.

Unsigned self-built executables may trigger Windows SmartScreen; code signing is a separate distribution step.
