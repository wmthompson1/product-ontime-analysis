#!/usr/bin/env pwsh

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Welcome to PowerShell on Replit!  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "PowerShell Version:" -ForegroundColor Yellow
$PSVersionTable.PSVersion

Write-Host "`nOperating System:" -ForegroundColor Yellow
if ($IsLinux) {
    Write-Host "Running on Linux (NixOS via Replit)" -ForegroundColor Green
}

Write-Host "`nCurrent Directory:" -ForegroundColor Yellow
Get-Location

Write-Host "`nEnvironment Variables (sample):" -ForegroundColor Yellow
Write-Host "HOME: $env:HOME"
Write-Host "USER: $env:USER"

Write-Host "`n✅ PowerShell is working perfectly!" -ForegroundColor Green
