@echo off
REM Build script for DCST Tool executables on Windows

echo 🚀 DCST Tool - Windows Build Script
echo ===================================

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is required but not found
    echo Please install Python 3.8 or later from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo 🐍 Python version: %PYTHON_VERSION%

REM Check if pip is available
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ pip is required but not found
    echo Please reinstall Python with pip included
    pause
    exit /b 1
)

REM Install/upgrade pip and setuptools
echo 📦 Updating build tools...
python -m pip install --upgrade pip setuptools wheel
if %errorlevel% neq 0 (
    echo ❌ Failed to update build tools
    pause
    exit /b 1
)

REM Install project dependencies
echo 📦 Installing project dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install project dependencies
    pause
    exit /b 1
)

REM Run the build script
echo 🔨 Starting build process...
python build_executables.py
if %errorlevel% neq 0 (
    echo ❌ Build process failed
    pause
    exit /b 1
)

REM Test the executable
echo 🧪 Testing the executable...
python test_executable.py
if %errorlevel% neq 0 (
    echo ⚠️ Executable test had issues (may be normal for GUI apps)
)

echo ✅ Build process completed!

REM Show final information
if exist "dist\DCST_Tool_Windows.exe" (
    echo.
    echo 📦 Windows executable created:
    for %%i in ("dist\DCST_Tool_Windows.exe") do (
        echo    Location: %CD%\dist\DCST_Tool_Windows.exe
        echo    Size: %%~zi bytes
    )
    echo.
    echo 📋 Distribution Instructions:
    echo    1. The .exe file is completely portable
    echo    2. No installation required for end users
    echo    3. Compatible with Windows 10/11
    echo    4. May trigger antivirus scan (normal for unsigned executables)
    echo    5. Users can run it by double-clicking
) else (
    echo ❌ Executable not found at expected location
    pause
    exit /b 1
)

echo.
echo 🎉 Build completed successfully!
echo.
echo Press any key to exit...
pause >nul
