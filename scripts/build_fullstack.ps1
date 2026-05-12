param(
    [switch]$SkipNpmInstall
)

$root = Resolve-Path "$PSScriptRoot\.."

& (Join-Path $PSScriptRoot "build_backend.ps1")
& (Join-Path $PSScriptRoot "build_portable.ps1")

$desktopRoot = Join-Path $root "DesktopApp"
if (-not (Test-Path $desktopRoot)) {
    throw "DesktopApp folder not found."
}

$desktopFrontend = Join-Path $desktopRoot "Frontend"
if (Test-Path $desktopFrontend) {
    Remove-Item -Recurse -Force $desktopFrontend
}
Copy-Item (Join-Path $root "Frontend") $desktopFrontend -Recurse -Force

$desktopBackend = Join-Path $desktopRoot "backend"
if (Test-Path $desktopBackend) {
    Remove-Item -Recurse -Force $desktopBackend
}
New-Item -ItemType Directory -Force -Path $desktopBackend | Out-Null
Copy-Item (Join-Path $root "dist\backend\LiteratureManagerBackend.exe") $desktopBackend -Force

Push-Location $desktopRoot
if (-not $SkipNpmInstall) {
    npm install
}
npm run dist
Pop-Location

Write-Host "Desktop app built at $desktopRoot\dist"
