param(
  [switch]$SkipExe,
  [switch]$CleanOnly,
  [switch]$AutoInstallPython
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$APP  = "vokaba"
$MAIN = "main.py"
$LOGO_PNG = "assets\vokaba_logo.png"

# -------------------------------------------------
# Python 3.11 ONLY (Kivy-safe)
# -------------------------------------------------
function Find-Python311 {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    return @{ Cmd = "py"; Args = @("-3.11") }
  }
  if (Get-Command python3.11 -ErrorAction SilentlyContinue) {
    return @{ Cmd = "python3.11"; Args = @() }
  }
  return $null
}

$pyInfo = Find-Python311

if (-not $pyInfo -and $AutoInstallPython -and (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Host "==> Installing Python 3.11..."
  winget install --id Python.Python.3.11 -e --silent | Out-Null
  $pyInfo = Find-Python311
}

if (-not $pyInfo) {
  throw "Python 3.11 not found (required for Kivy on Windows)."
}

$PyCmd  = $pyInfo.Cmd
$PyArgs = $pyInfo.Args

# -------------------------------------------------
# Version
# -------------------------------------------------
$match = Select-String -Path $MAIN -Pattern '__version__\s*=\s*["''](.+?)["'']'
if (-not $match) { throw "__version__ not found in $MAIN" }
$VERSION = $match.Matches[0].Groups[1].Value

# -------------------------------------------------
# Output / Clean
# -------------------------------------------------
$Docs   = [Environment]::GetFolderPath("MyDocuments")
$OUTDIR = Join-Path $Docs ("Vokaba-releases\vokaba-" + $VERSION)

Remove-Item -Recurse -Force $OUTDIR,".venv-win","build-win","dist-win" `
  -ErrorAction SilentlyContinue

if ($CleanOnly) {
  Write-Host "Clean done."
  exit 0
}

New-Item -ItemType Directory -Force -Path $OUTDIR | Out-Null

# -------------------------------------------------
# EXE
# -------------------------------------------------
if (-not $SkipExe) {
  Write-Host "==> Building Windows portable .exe (ONEFILE)"

  if (-not (Test-Path $LOGO_PNG)) {
    throw "Logo not found: $LOGO_PNG"
  }

  # ---- venv
  & $PyCmd @PyArgs -m venv ".venv-win"
  $venvPy = ".venv-win\Scripts\python.exe"

  & $venvPy -m pip install --upgrade pip wheel
  & $venvPy -m pip install -r requirements.txt
  & $venvPy -m pip install pyinstaller pillow

# ---- Icon (fertig vorhanden)
$ICON = (Resolve-Path "assets\vokaba_logo.ico").Path
$AssetsPath = (Resolve-Path "assets").Path

& $venvPy -m PyInstaller `
  --name $APP `
  --onefile `
  --windowed `
  --icon "$ICON" `
  --clean `
  --noconfirm `
  --distpath dist-win `
  --workpath build-win `
  --specpath build-win `
  --add-data "$AssetsPath;assets" `
  $MAIN


  $exe = "dist-win\$APP.exe"
  if (-not (Test-Path $exe)) { throw "EXE not found" }

  Move-Item $exe (Join-Path $OUTDIR ("vokaba-" + $VERSION + "-win64.exe")) -Force
}

Write-Host ""
Write-Host "Windows build finished"
Write-Host "Output in $OUTDIR"
