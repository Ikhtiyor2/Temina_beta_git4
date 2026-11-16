# Bubblewrap init через локальный HTTP (Bubblewrap не принимает file:// и локальный путь C:\...)
# Запуск из корня репозитория:
#   powershell -ExecutionPolicy Bypass -File pushup_site/twa/init-bubblewrap.ps1

$ErrorActionPreference = "Stop"
$twaDir = $PSScriptRoot
$staticDir = [System.IO.Path]::GetFullPath((Join-Path $twaDir "..\static"))
$manifest = Join-Path $staticDir "manifest.json"

if (-not (Test-Path -LiteralPath $manifest)) {
    Write-Error "Файл не найден: $manifest"
}

$port = 4173
$manifestUrl = "http://127.0.0.1:$port/manifest.json"
Write-Host "Static dir: $staticDir"
Write-Host "Manifest URL: $manifestUrl"

# выбираем интерпретатор для http.server
$pyCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $pyCmd = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyCmd = "python" }
else {
    Write-Error "Не найден Python (py/python) для локального HTTP сервера."
}

$server = Start-Process -FilePath $pyCmd -ArgumentList "-m","http.server","$port" -WorkingDirectory $staticDir -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

try {
    npx @bubblewrap/cli init --manifest="$manifestUrl"
}
finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}
