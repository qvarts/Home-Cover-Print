$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Project virtual environment was not found: $Python"
}

& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller is not installed. Installing it in the project environment..."
    & $Python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install PyInstaller."
    }
}

Write-Host "Generating application icon..."
& $Python "build_icon.py"
if ($LASTEXITCODE -ne 0) {
    throw "Could not generate application icon."
}

Write-Host "Building Home Cover Print..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "HomeCoverPrint" `
    --icon "home_cover_print.ico" `
    main.py

if ($LASTEXITCODE -ne 0) {
    throw "Build failed."
}

$Output = Join-Path $ProjectRoot "dist\HomeCoverPrint.exe"
Write-Host ""
Write-Host "Build completed:"
Write-Host $Output
