#!/usr/bin/env pwsh

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Data Processing Example           " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$manufacturingData = @(
    [PSCustomObject]@{ PartNumber = "A101"; Quantity = 150; DefectRate = 0.02; Status = "Pass" }
    [PSCustomObject]@{ PartNumber = "B202"; Quantity = 200; DefectRate = 0.01; Status = "Pass" }
    [PSCustomObject]@{ PartNumber = "C303"; Quantity = 175; DefectRate = 0.05; Status = "Review" }
    [PSCustomObject]@{ PartNumber = "D404"; Quantity = 225; DefectRate = 0.03; Status = "Pass" }
    [PSCustomObject]@{ PartNumber = "E505"; Quantity = 190; DefectRate = 0.08; Status = "Fail" }
)

Write-Host "Manufacturing Data:" -ForegroundColor Yellow
$manufacturingData | Format-Table -AutoSize

Write-Host "`nStatistical Summary:" -ForegroundColor Yellow
$totalQuantity = ($manufacturingData | Measure-Object -Property Quantity -Sum).Sum
$avgDefectRate = ($manufacturingData | Measure-Object -Property DefectRate -Average).Average

Write-Host "  Total Parts Processed: $totalQuantity"
Write-Host "  Average Defect Rate: $($avgDefectRate.ToString('P2'))"

Write-Host "`nFiltering: Parts with Defect Rate > 3%:" -ForegroundColor Yellow
$highDefects = $manufacturingData | Where-Object { $_.DefectRate -gt 0.03 }
$highDefects | Format-Table -AutoSize

Write-Host "`nGrouping by Status:" -ForegroundColor Yellow
$manufacturingData | Group-Object -Property Status | ForEach-Object {
    Write-Host "  $($_.Name): $($_.Count) parts" -ForegroundColor $(
        switch ($_.Name) {
            "Pass" { "Green" }
            "Review" { "Yellow" }
            "Fail" { "Red" }
        }
    )
}

Write-Host "`nExporting to CSV..." -ForegroundColor Yellow
$csvPath = "powershell-scripts/test-data/manufacturing_data.csv"
$manufacturingData | Export-Csv -Path $csvPath -NoTypeInformation
Write-Host "✅ Data exported to: $csvPath" -ForegroundColor Green

Write-Host "`n✅ Data processing completed!" -ForegroundColor Green
