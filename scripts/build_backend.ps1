param(
    [string]$OutputDir = "$PSScriptRoot\..\dist\backend"
)

$root = Resolve-Path "$PSScriptRoot\.."
$entrypoint = Join-Path $root "Backend\packaging\entrypoint.py"
$backendPath = Join-Path $root "Backend"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }
$distPath = Resolve-Path $OutputDir -ErrorAction SilentlyContinue
if (-not $distPath) {
    $distPath = $OutputDir
}
$workPath = Join-Path $root "dist\backend\build"
$specPath = Join-Path $root "dist\backend\spec"

New-Item -ItemType Directory -Force -Path $distPath | Out-Null
New-Item -ItemType Directory -Force -Path $workPath | Out-Null
New-Item -ItemType Directory -Force -Path $specPath | Out-Null

& $pythonCmd -m PyInstaller --onefile --name LiteratureManagerBackend --noconfirm --clean --paths $backendPath --distpath $distPath --workpath $workPath --specpath $specPath $entrypoint
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Backend exe built at $distPath\LiteratureManagerBackend.exe"
