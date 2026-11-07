param(
    [switch]$OneFile,
    [string]$OutputName = 'InvoiceFlow_3.0.0',
    [string]$Version = '3.0.0',
    [switch]$Installer,
    [switch]$SkipPyInstaller
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root
$mode = if ($OneFile) { '--onefile' } else { '--onedir' }
$icon = Join-Path $root 'assets\brand\invoiceflow-if-logo.ico'
$data = "$root\assets\brand;assets\brand"
$dist = Join-Path $root "dist\$OutputName"
$work = Join-Path $root "build\$OutputName"
if (-not $SkipPyInstaller) {
    python -m PyInstaller --noconfirm --clean $mode --windowed --name InvoiceFlow --icon $icon --add-data $data --paths $root --specpath (Join-Path $root 'packaging\windows') --workpath $work --distpath $dist main.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
}
if (-not (Test-Path (Join-Path $dist 'InvoiceFlow\InvoiceFlow.exe'))) {
    throw "PyInstaller output was not found: $dist\InvoiceFlow\InvoiceFlow.exe"
}
Write-Host "Using $dist\InvoiceFlow"

if ($Installer) {
    $iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
    if (-not $iscc) {
        $candidates = @(
            'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
            'C:\Program Files\Inno Setup 6\ISCC.exe',
            (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
        )
        $iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not $iscc) {
        throw 'Inno Setup compiler (ISCC.exe) was not found. Install Inno Setup 6 before using -Installer.'
    }
    if ($Version -notmatch '^\d+\.\d+\.\d+$') {
        throw "Version must use semantic version format, received: $Version"
    }
    $script = Join-Path $root 'packaging\windows\installer.iss'
    $outputDir = Join-Path $root "dist\$OutputName"
    $installerName = "InvoiceFlow_Setup_$Version"
    & $iscc "/DMyAppVersion=$Version" "/DDistributionDir=$outputDir\InvoiceFlow" "/DOutputDir=$outputDir" "/DInstallerName=$installerName" /Qp $script
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }
    $installerPath = "$outputDir\$installerName.exe"
    if (-not (Test-Path $installerPath)) {
        throw "Installer output was not created: $installerPath"
    }
    $hash = Get-FileHash -Algorithm SHA256 $installerPath
    $checksum = "$($hash.Hash)  $([IO.Path]::GetFileName($installerPath))"
    Set-Content -LiteralPath "$installerPath.sha256" -Value $checksum -Encoding ascii
    Write-Host "Built $installerPath"
    Write-Host "Checksum $($hash.Hash)"
}
