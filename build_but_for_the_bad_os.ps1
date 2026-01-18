param(
  [switch]$SkipExe,
  [switch]$SkipSourceZip,
  [switch]$CleanOnly,
  [switch]$AutoInstallPython
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$APP  = "vokaba"
$MAIN = "main.py"

function Find-Python {
  if (Get-Command py -ErrorAction SilentlyContinue) { return @("py","-3") }
  if (Get-Command python -ErrorAction SilentlyContinue) { return @("python") }
  return $null
}

$py = Find-Python
if (-not $py -and $AutoInstallPython -and (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Host "==> Installing Python via winget (may take a moment)..."
  winget install --id Python.Python.3.11 -e --silent | Out-Null
  $py = Find-Python
}

if (-not $py) {
  throw "Python not found. Install Python 3.11+ (python.org / winget) and rerun."
}

# Read version from main.py (regex)
$match = Select-String -Path $MAIN -Pattern '__version__\s*=\s*["''](.+?)["'']' -AllMatches
if (-not $match.Matches.Count) { throw "__version__ not found in $MAIN" }
$VERSION = $match.Matches[0].Groups[1].Value

# Documents path (localized-safe)
$Docs = [Environment]::GetFolderPath("MyDocuments")
$OUTBASE = Join-Path $Docs "Vokaba-releases"
$OUTDIR  = Join-Path $OUTBASE ("vokaba-" + $VERSION)

# Clean
if (Test-Path $OUTDIR) { Remove-Item -Recurse -Force $OUTDIR }
Remove-Item -Recurse -Force ".venv-win","build-win","dist-win" -ErrorAction SilentlyContinue

if ($CleanOnly) {
  Write-Host "✅ Clean done."
  exit 0
}

New-Item -ItemType Directory -Force -Path $OUTDIR | Out-Null

# -------------------------------------------------
# Source code zip
# -------------------------------------------------
if (-not $SkipSourceZip) {
  Write-Host "==> Building source zip"
  $ZipPath = Join-Path $OUTDIR ("vokaba-" + $VERSION + "-source.zip")

  $excludeRegex = '\\(\.git|\.idea|__pycache__|venv|\.venv|\.venv-win|build|dist|build-win|dist-win|AppDir|deb-build)\\'
  $files = Get-ChildItem -Recurse -File | Where-Object {
    $_.FullName -notmatch $excludeRegex -and
    $_.Name -notin @("appimagetool.AppImage") -and
    $_.Extension -notin @(".pyc",".pyo")
  }

  if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
  Compress-Archive -Path $files.FullName -DestinationPath $ZipPath -Force
  Get-Item $ZipPath | Format-List Name,Length,FullName
}

# -------------------------------------------------
# EXE (portable ONEFILE)
# -------------------------------------------------
if (-not $SkipExe) {
  Write-Host "==> Building Windows portable .exe (ONEFILE)"

  $VENV = ".venv-win"
  & $py @("-m","venv",$VENV)

  $venvPy = Join-Path $VENV "Scripts\python.exe"
  & $venvPy -m pip install --upgrade pip wheel
  & $venvPy -m pip install -r requirements.txt
  & $venvPy -m pip install pyinstaller

  Remove-Item -Recurse -Force "build-win","dist-win" -ErrorAction SilentlyContinue

  # Windows --add-data uses ';'
  & $venvPy -m PyInstaller `
    --name $APP `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --distpath dist-win `
    --workpath build-win `
    --specpath build-win `
    --add-data "assets;assets" `
    $MAIN

  $exe = Join-Path "dist-win" ($APP + ".exe")
  if (-not (Test-Path $exe)) { throw "EXE not found at $exe" }

  $outExe = Join-Path $OUTDIR ("vokaba-" + $VERSION + "-win64.exe")
  Move-Item $exe $outExe -Force
  Get-Item $outExe | Format-List Name,Length,FullName
}

Write-Host ""
Write-Host "✅ Windows build finished"
Write-Host ("📦 Output in: " + $OUTDIR)
