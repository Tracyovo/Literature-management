param(
    [string]$OutputDir = "portable"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$ReleaseRoot = Join-Path $Root $OutputDir
$AppDir = Join-Path $ReleaseRoot "LiteratureManager"
$BuildDir = Join-Path $ReleaseRoot "_build"
$DistDir = Join-Path $ReleaseRoot "_dist"

if (Test-Path $AppDir) {
    Remove-Item $AppDir -Recurse -Force
}
if (Test-Path $BuildDir) {
    Remove-Item $BuildDir -Recurse -Force
}
if (Test-Path $DistDir) {
    Remove-Item $DistDir -Recurse -Force
}

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    throw "Python venv not found: $python"
}

Push-Location (Join-Path $Root "Backend")
& $python -m PyInstaller \
    --noconfirm \
    --onefile \
    --name LiteratureManagerBackend \
    --distpath $DistDir \
    --workpath $BuildDir \
    --specpath $BuildDir \
    --collect-submodules app \
    run.py
Pop-Location

$exe = Join-Path $DistDir "LiteratureManagerBackend.exe"
if (!(Test-Path $exe)) {
    throw "Build failed: $exe not found"
}

New-Item -ItemType Directory -Path $AppDir | Out-Null
Copy-Item $exe $AppDir
Copy-Item (Join-Path $Root "Frontend") (Join-Path $AppDir "Frontend") -Recurse
Copy-Item (Join-Path $Root "launch_portable.bat") $AppDir

$manualPath = Join-Path $Root "docs\user-manual.html"
if (Test-Path $manualPath) {
    Copy-Item $manualPath (Join-Path $AppDir "USER_MANUAL.html")
}

New-Item -ItemType Directory -Path (Join-Path $AppDir "uploads") | Out-Null

Write-Host "Portable release created at: $AppDir"
