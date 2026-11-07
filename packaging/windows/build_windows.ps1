param([switch]$OneFile)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root
$mode = if ($OneFile) { '--onefile' } else { '--onedir' }
python -m PyInstaller --noconfirm --clean $mode --windowed --name InvoiceFlow --paths $root --specpath (Join-Path $root 'packaging\windows') --workpath (Join-Path $root 'build') --distpath (Join-Path $root 'dist') main.py
Write-Host "Built $root\dist\InvoiceFlow"
