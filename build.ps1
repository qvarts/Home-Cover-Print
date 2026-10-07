param (
    [Parameter(Mandatory=$false)]
    [switch]$Clean
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Log {
    param (
        [string]$Message,
        [ConsoleColor]$Color = "White",
        [switch]$NewLine = $false
    )
    if ($NewLine) { Write-Host "`n" }
    Write-Host $Message -ForegroundColor $Color
}

Write-Log "`n"
Write-Log "================================================================================" -Color Magenta
Write-Log "   HOME COVER PRINT - Build Process" -Color Magenta
Write-Log "================================================================================" -Color Magenta
Write-Log "`n"

# --- [0/4] Version Extraction ---
$VersionFile = Join-Path $ProjectRoot "src\version.py"
if (Test-Path $VersionFile) {
    $VersionLine = Get-Content $VersionFile | Select-String "__version__"
    if ($VersionLine) {
        $Version = ($VersionLine -split '"')[1]
        if (-not $Version) { $Version = ($VersionLine -split "'")[1] }
    } else {
        $Version = "0.0.0"
    }
} else {
    $Version = "0.0.0"
}
$ExeName = "HomeCoverPrint_win_$Version"

# Always clean build directory to prevent PyInstaller cache issues
Write-Log "--- [1/4] Workspace Cleanup ---" -Color Cyan
$BuildPath = Join-Path $ProjectRoot "build"
if (Test-Path $BuildPath) {
    Write-Log "  [!] Purging build cache..." -Color Yellow
    Remove-Item -Recurse -Force $BuildPath
    Write-Log "  [+] Build directory cleared." -Color Green
} else {
    Write-Log "  [+] Build directory already clean." -Color Green
}
Write-Log "`n"

Write-Log "--- [2/4] Bootstrapping Environment ---" -Color Cyan

# Check Python
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Log "  [!] Python not found in PATH." -Color Red
    exit 1
}

$VenvPath = Join-Path $ProjectRoot ".venv"
$Python = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Log "  [!] Virtual environment not found. Creating one..." -Color Yellow
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit 1 }
    Write-Log "  [+] Virtual environment created successfully." -Color Green
} else {
    Write-Log "  [+] Existing virtual environment found." -Color Green
}

Write-Log "`n  Updating dependencies..." -Color Cyan
& $Python -m pip install --upgrade pip

Write-Log "  Installing build tools..." -Color Cyan
& $Python -m pip install pyinstaller pillow
if ($LASTEXITCODE -ne 0) { exit 1 }

if (Test-Path "requirements.txt") {
    Write-Log "  Installing project requirements from requirements.txt..." -Color Cyan
    & $Python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

Write-Log "`n  [+] Environment Ready.`n" -Color Green

Write-Log "--- [3/4] Asset Generation ---" -Color Cyan
$RequiredAssets = @("home_cover_print.svg", "main.py", "build_icon.py")
foreach ($Asset in $RequiredAssets) {
    if (-not (Test-Path $Asset)) {
        Write-Log "  [!] Required asset missing: $Asset." -Color Red
        exit 1
    }
}

Write-Log "  Generating application icon..." -Color Cyan
& $Python "build_icon.py"
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Log "  [+] Icon generated successfully." -Color Green
Write-Log "`n"

Write-Log "--- [4/4] Final Compilation ---" -Color Cyan
Write-Log "  Starting PyInstaller build process..." -Color Cyan

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "$ExeName" `
    --icon "home_cover_print.ico" `
    --add-data "home_cover_print.svg;." `
    --add-data "home_cover_print.ico;." `
    main.py

if ($LASTEXITCODE -ne 0) {
    Write-Log "  [!] PyInstaller failed with exit code $LASTEXITCODE." -Color Red
    exit 1
}

# --- Post-build Cleanup (Silent) ---
$SpecFile = "$ExeName.spec"
if (Test-Path $SpecFile) {
    Remove-Item $SpecFile
}
if (Test-Path $BuildPath) {
    Remove-Item -Recurse -Force $BuildPath
}

$Output = Join-Path $ProjectRoot "dist\$ExeName.exe"
Write-Log "`n"
Write-Log "================================================================================" -Color Green
Write-Log "  BUILD COMPLETED SUCCESSFULLY!" -Color Green
Write-Log "================================================================================" -Color Green
Write-Log "`nExecutable path: " -NoNewline
Write-Log $Output -Color Yellow
Write-Log "`n"
