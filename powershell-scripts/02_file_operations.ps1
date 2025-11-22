#!/usr/bin/env pwsh

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  File Operations Example           " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$testDir = "powershell-scripts/test-data"
$testFile = "$testDir/sample.txt"

Write-Host "Creating test directory..." -ForegroundColor Yellow
if (-not (Test-Path $testDir)) {
    New-Item -ItemType Directory -Path $testDir | Out-Null
    Write-Host "✅ Directory created: $testDir" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Directory already exists: $testDir" -ForegroundColor Blue
}

Write-Host "`nWriting sample data to file..." -ForegroundColor Yellow
$sampleData = @"
Manufacturing Data Processing with PowerShell
==============================================
Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Environment: Replit (NixOS)

This is a sample file created by PowerShell.
Perfect for data processing, automation, and scripting!
"@

Set-Content -Path $testFile -Value $sampleData
Write-Host "✅ File created: $testFile" -ForegroundColor Green

Write-Host "`nReading file content:" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Gray
Get-Content -Path $testFile
Write-Host "------------------------" -ForegroundColor Gray

Write-Host "`nFile Statistics:" -ForegroundColor Yellow
$fileInfo = Get-Item -Path $testFile
Write-Host "  Size: $($fileInfo.Length) bytes"
Write-Host "  Created: $($fileInfo.CreationTime)"
Write-Host "  Modified: $($fileInfo.LastWriteTime)"

Write-Host "`n✅ File operations completed successfully!" -ForegroundColor Green
