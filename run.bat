@echo off
title Aura AI Assistant
cd /d "%~dp0"

echo ===================================================
echo   Aura - Modular AI Assistant
echo ===================================================

REM Use the project-local Python interpreter
set PYTHON="%~dp0.venv\Scripts\python.exe"

if not exist %PYTHON% (
    echo [ERROR] Python interpreter not found at .venv\Scripts\python.exe
    echo Please run setup first.
    pause
    exit /b 1
)

echo [Aura] Using Python: %PYTHON%
echo [Aura] Starting Aura assistant...
echo [Aura] Press Ctrl+C to stop.
echo.

%PYTHON% main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Aura] Exited with error code %ERRORLEVEL%.
    echo Check the output above for details.
    pause
)
