# Full build: grabber_host.exe → (guide images) → dist\Grabber-Setup.exe + SHA256
#   powershell -File src\build.ps1               local build, re-renders the guide images
#   powershell -File src\build.ps1 -SkipRender   use the committed docs\ images (CI does this)
param([switch]$SkipRender)
$ErrorActionPreference = 'Stop'
$src = $PSScriptRoot
$root = Split-Path $src
$work = Join-Path $env:TEMP 'grabber-build'
$version = (Get-Content "$root\extension\manifest.json" -Raw | ConvertFrom-Json).version

python -m PyInstaller --noconfirm --clean --onedir --console --name grabber_host --icon "$src\icon.ico" `
    --distpath $work --workpath "$work\build" --specpath $work "$src\host.py"
if ($LASTEXITCODE) { throw 'PyInstaller failed' }

if (-not $SkipRender) { & "$src\readme\render.ps1" }

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw 'Inno Setup 6 not found: winget install JRSoftware.InnoSetup' }
& $iscc /Q "/DAppDir=$work\grabber_host" "/DAppVer=$version" "$src\setup.iss"
if ($LASTEXITCODE) { throw 'Inno Setup failed' }

$exe = "$root\dist\Grabber-Setup.exe"
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
"$hash  Grabber-Setup.exe" | Set-Content "$root\dist\SHA256SUMS.txt" -Encoding ascii
Write-Host "OK: $exe  v$version  sha256 $hash"
