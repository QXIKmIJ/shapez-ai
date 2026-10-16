@echo off
title Shapez AI Master Orchestrator
echo ========================================================
echo   Shapez AI Autonomous Cognitive Orchestrator
echo   Author: QXIK_mIJ
echo   Autonomous factory builder ^& self-healing watchdog
echo ========================================================
echo.

set SCRIPT_DIR=%~dp0
set PYTHON_PATH=python

echo [1/3] Checking LLM Engine status (http://127.0.0.1:18088/health)...
curl -s http://127.0.0.1:18088/health >nul
if %errorlevel% neq 0 (
    if exist "D:\engine\bin\llama-b11524\llama-server.exe" (
        echo [INFO] Starting local llama-server on port 18088...
        start "Shapez AI - LLM Server" /min "D:\engine\bin\llama-b11524\llama-server.exe" -m "D:\Qwen3.5-9B-Q8_0\Qwen3.5-9B-Q8_0.gguf" --mmproj "D:\Qwen3.5-9B-Q8_0\mmproj-F16.gguf" --port 18088 -ngl 28 -c 4096 --host 127.0.0.1 --reasoning-budget 0
        timeout /t 3 /nobreak >nul
    ) else (
        echo [INFO] Local llama-server binary not found. Shapez AI will use deterministic tactical planning or configured endpoint.
    )
) else (
    echo [OK] LLM inference engine is online on port 18088!
)

echo.
echo [2/3] Checking Shapez Game installation...
if exist "%SCRIPT_DIR%shapez.exe" (
    echo [OK] Found local shapez.exe executable.
) else (
    echo [INFO] Running with external/Steam Shapez version. Ensure shapez-ai-bridge mod is installed (run install_mod.bat).
)

echo.
echo [3/3] Starting Shapez AI Python Orchestrator on ws://127.0.0.1:8765 ...
cd /d "%SCRIPT_DIR%shapez-ai\python"
python -u main.py
pause
