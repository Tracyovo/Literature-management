param(
    [string]$OutputDir = "release"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$ReleaseRoot = Join-Path $Root $OutputDir
$AppDir = Join-Path $ReleaseRoot "LiteratureManager"

if (Test-Path $AppDir) {
    Remove-Item $AppDir -Recurse -Force
}

New-Item -ItemType Directory -Path $AppDir | Out-Null

$backendDir = Join-Path $AppDir "Backend"
$frontendDir = Join-Path $AppDir "Frontend"

New-Item -ItemType Directory -Path $backendDir | Out-Null
New-Item -ItemType Directory -Path $frontendDir | Out-Null

Copy-Item (Join-Path $Root "Backend\app") $backendDir -Recurse
Copy-Item (Join-Path $Root "Backend\requirements.txt") $backendDir
Copy-Item (Join-Path $Root "Backend\run.py") $backendDir

Copy-Item (Join-Path $Root "Frontend\*") $frontendDir -Recurse

Copy-Item (Join-Path $Root "start.bat") $AppDir
Copy-Item (Join-Path $Root "start.sh") $AppDir
Copy-Item (Join-Path $Root "launch.bat") $AppDir

$manualPath = Join-Path $Root "docs\user-manual.html"
if (Test-Path $manualPath) {
    Copy-Item $manualPath (Join-Path $AppDir "USER_MANUAL.html")
}

$uploadsDir = Join-Path $backendDir "uploads"
New-Item -ItemType Directory -Path $uploadsDir | Out-Null

Write-Host "Release created at: $AppDir"
