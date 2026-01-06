@echo off
REM KCLI Build Script for Windows
REM Creates a standalone .exe installer

echo.
echo  KCLI Desktop Commander - Build Script
echo  =====================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    exit /b 1
)

REM Install build dependencies
echo [1/3] Installing build dependencies...
pip install pyinstaller httpx colorama --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

REM Build executable
echo [2/3] Building executable...
pyinstaller --onefile --name kcli --console kcli/__main__.py
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

REM Verify build
echo [3/3] Verifying build...
if exist "dist\kcli.exe" (
    echo.
    echo  BUILD SUCCESSFUL!
    echo  ================
    echo  Executable: dist\kcli.exe
    echo.
    echo  To install system-wide:
    echo    copy dist\kcli.exe C:\Windows\System32\
    echo.
    echo  Or add dist\ to your PATH
    echo.
) else (
    echo ERROR: Build output not found
    exit /b 1
)

pause
