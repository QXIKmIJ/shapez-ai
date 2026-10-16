# Shapez AI - In-Game Mod Installer
# Author: QXIK_mIJ
# License: Apache License 2.0

Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "   Shapez AI - In-Game Mod Installer" -ForegroundColor Cyan
Write-Host "   Author: QXIK_mIJ" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host ""

$TargetDir = "$env:APPDATA\shapez.io\mods"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceFile = Join-Path $ScriptDir "shapez-ai\mod\shapez-ai-bridge.js"

if (-not (Test-Path $SourceFile)) {
    Write-Host "[ERROR] Source file not found: $SourceFile" -ForegroundColor Red
    pause
    exit 1
}

if (-not (Test-Path $TargetDir)) {
    Write-Host "[INFO] Creating directory: $TargetDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

Copy-Item -Path $SourceFile -Destination (Join-Path $TargetDir "shapez-ai-bridge.js") -Force

Write-Host "[OK] Shapez AI Bridge mod successfully installed to:" -ForegroundColor Green
Write-Host "     $TargetDir\shapez-ai-bridge.js" -ForegroundColor White
Write-Host ""
Write-Host "Now you can launch Shapez (Steam, portable or web version)." -ForegroundColor Cyan
Write-Host "The mod will automatically load and connect to Shapez AI!" -ForegroundColor Green
Write-Host ""
pause
