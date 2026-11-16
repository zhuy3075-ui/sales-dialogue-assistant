$ErrorActionPreference = 'Stop'
$installer = Join-Path $PSScriptRoot 'scripts\setup_wechat.py'
foreach ($candidate in @('python', 'python3')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
        & $command.Source -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { & $command.Source -B -X utf8 $installer @args; exit $LASTEXITCODE }
    }
}
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCommand) {
    & $uvCommand.Source run --no-project --python 3.12 python -B -X utf8 $installer @args
    exit $LASTEXITCODE
}
# User-local bootstrap only. No admin elevation or global PATH changes.
$bootstrap = Join-Path $env:USERPROFILE '.sales-dialogue-assistant\bootstrap\uv-0.7.22'
New-Item -ItemType Directory -Path $bootstrap -Force | Out-Null
$cpu = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'aarch64' } else { 'x86_64' }
$asset = "uv-$cpu-pc-windows-msvc.zip"
$base = 'https://github.com/astral-sh/uv/releases/download/0.7.22'
$archive = Join-Path $bootstrap $asset
$checksum = Join-Path $bootstrap "$asset.sha256"
Invoke-WebRequest -Uri "$base/$asset" -OutFile $archive
Invoke-WebRequest -Uri "$base/$asset.sha256" -OutFile $checksum
$expected = ((Get-Content -LiteralPath $checksum -Raw).Trim() -split '\s+')[0]
$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw 'uv checksum mismatch; no executable was run.' }
Expand-Archive -LiteralPath $archive -DestinationPath $bootstrap -Force
$uvBinary = Get-ChildItem -LiteralPath $bootstrap -Filter 'uv.exe' -Recurse | Select-Object -First 1
if (-not $uvBinary) { throw 'uv.exe missing from archive.' }
& $uvBinary.FullName run --no-project --python 3.12 python -B -X utf8 $installer @args
exit $LASTEXITCODE
