# Start Shapez AI Master Orchestrator
# Author: QXIK_mIJ
# License: Apache License 2.0

Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "   Shapez AI Autonomous Cognitive Orchestrator" -ForegroundColor Cyan
Write-Host "   Author: QXIK_mIJ" -ForegroundColor White
Write-Host "   Autonomous factory builder & self-healing watchdog" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Check LLM Server
$LlamaPath = "D:\engine\bin\llama-b11524\llama-server.exe"
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:18088/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] LLM inference engine online on port 18088." -ForegroundColor Green
} catch {
    if (Test-Path $LlamaPath) {
        Write-Host "[INFO] Starting local llama-server on port 18088..." -ForegroundColor Yellow
        Start-Process -FilePath $LlamaPath `
            -ArgumentList "-m D:\Qwen3.5-9B-Q8_0\Qwen3.5-9B-Q8_0.gguf --mmproj D:\Qwen3.5-9B-Q8_0\mmproj-F16.gguf --port 18088 -ngl 28 -c 4096 --host 127.0.0.1 --reasoning-budget 0" `
            -WindowStyle Minimized
        Start-Sleep -Seconds 3
    } else {
        Write-Host "[INFO] Local llama-server binary not found. Running with deterministic tactical planner or configured endpoint." -ForegroundColor DarkCyan
    }
}

# 2. Check Game executable
if (Test-Path "$ScriptDir\shapez.exe") {
    Write-Host "[OK] Found local shapez.exe executable." -ForegroundColor Green
} else {
    Write-Host "[INFO] Running with external/Steam Shapez version. Ensure shapez-ai-bridge is installed (run install_mod.ps1)." -ForegroundColor DarkCyan
}

Write-Host ""
Write-Host "[INFO] Starting Shapez AI Python Orchestrator on ws://127.0.0.1:8765 ..." -ForegroundColor Cyan
Set-Location -Path "$ScriptDir\shapez-ai\python"
python -u main.py
