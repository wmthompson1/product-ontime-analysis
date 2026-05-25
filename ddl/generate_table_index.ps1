<#
Generates TABLE_INDEX.md mapping table name -> relative SQL file path.
Canonical DDL location: Utilities\SQLMesh\ddl\
Run from repository root (or this script will compute paths relative to repo root).
#>
$out = Join-Path -Path $PSScriptRoot -ChildPath 'TABLE_INDEX.md'
Write-Output ("Generating table index to: $out")

Write-Output "Scanning $PSScriptRoot for .sql files..."
$files = Get-ChildItem -Path $PSScriptRoot -File -Filter '*.sql' -ErrorAction SilentlyContinue

"# Table index for Utilities/SQLMesh/ddl" | Out-File -FilePath $out -Encoding utf8
"" | Out-File -FilePath $out -Encoding utf8 -Append
"This file maps table names (derived from filenames) to the extracted CREATE script files." | Out-File -FilePath $out -Encoding utf8 -Append
"" | Out-File -FilePath $out -Encoding utf8 -Append
"| Table | File |" | Out-File -FilePath $out -Encoding utf8 -Append
"| --- | --- |" | Out-File -FilePath $out -Encoding utf8 -Append

foreach ($f in $files | Sort-Object -Property Name) {
    $name = $f.BaseName
    if ($name -match '\.') {
        $tbl = $name.Split('.')[1]
    } else {
        $tbl = $name
    }
    # Use the file name (including schema prefix) so the reference is clear
    $rel = $f.Name
    "| $tbl | $rel |" | Out-File -FilePath $out -Encoding utf8 -Append
}

Write-Output "Wrote TABLE_INDEX.md with $($files.Count) entries."
