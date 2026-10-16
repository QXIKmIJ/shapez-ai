@echo off
title Shapez AI - Mod Installer
echo ========================================================
echo   Shapez AI - In-Game Mod Installer
echo   Author: QXIK_mIJ
echo   Target: %%APPDATA%%\shapez.io\mods
echo ========================================================
echo.

set TARGET_DIR=%APPDATA%\shapez.io\mods
set SOURCE_FILE=%~dp0shapez-ai\mod\shapez-ai-bridge.js

if not exist "%SOURCE_FILE%" (
    echo [ERROR] Source file not found: %SOURCE_FILE%
    pause
    exit /b 1
)

if not exist "%TARGET_DIR%" (
    echo [INFO] Creating directory: %TARGET_DIR%
    mkdir "%TARGET_DIR%"
)

copy /y "%SOURCE_FILE%" "%TARGET_DIR%\shapez-ai-bridge.js" >nul
if %errorlevel% equ 0 (
    echo [OK] Shapez AI Bridge mod successfully installed to:
    echo      %TARGET_DIR%\shapez-ai-bridge.js
    echo.
    echo Now you can launch Shapez (Steam, portable or web version).
    echo The mod will automatically load and connect to Shapez AI!
) else (
    echo [ERROR] Failed to copy mod file. Please check folder permissions.
)

echo.
pause
