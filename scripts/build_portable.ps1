param(
    [string]$OutputDir = "$PSScriptRoot\..\dist\portable"
)

$root = Resolve-Path "$PSScriptRoot\.."
$backendExe = Join-Path $root "dist\backend\LiteratureManagerBackend.exe"
if (-not (Test-Path $backendExe)) {
    throw "Backend exe not found. Run scripts\build_backend.ps1 first."
}

$portablePath = Resolve-Path $OutputDir -ErrorAction SilentlyContinue
if ($portablePath) {
    Remove-Item -Recurse -Force $portablePath
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Copy-Item $backendExe (Join-Path $OutputDir "LiteratureManagerBackend.exe") -Force
Copy-Item (Join-Path $root "Frontend") (Join-Path $OutputDir "Frontend") -Recurse -Force
Copy-Item (Join-Path $root "launch_portable.bat") (Join-Path $OutputDir "launch_portable.bat") -Force

Write-Host "Portable build ready at $OutputDir"
