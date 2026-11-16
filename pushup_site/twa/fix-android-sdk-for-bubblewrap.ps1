# Bubblewrap проверяет папку "bin" или "tools" в корне Android SDK.
# Создаём junction Sdk\bin -> ...\cmdline-tools\<версия>\bin
#
# В Android Studio: SDK Manager → SDK Tools → Android SDK Command-line Tools.

$ErrorActionPreference = "Stop"
$sdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$targetBin = Join-Path $sdk "bin"

function Find-CmdlineBin {
    param([string]$SdkRoot)
    $latest = Join-Path $SdkRoot "cmdline-tools\latest\bin"
    if (Test-Path $latest) { return $latest }
    $ct = Join-Path $SdkRoot "cmdline-tools"
    if (-not (Test-Path $ct)) { return $null }
    Get-ChildItem $ct -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $b = Join-Path $_.FullName "bin"
        if ((Test-Path $b) -and (Test-Path (Join-Path $b "sdkmanager.bat"))) { $b }
    } | Select-Object -First 1
}

if (-not (Test-Path $sdk)) {
    Write-Error "Папка SDK не найдена: $sdk"
}

$cmdBin = Find-CmdlineBin $sdk
if (-not $cmdBin) {
    Write-Host @"
Не найден cmdline-tools\...\bin\sdkmanager.bat
Установите: Android Studio → Settings → Android SDK → вкладка SDK Tools →
«Android SDK Command-line Tools» → Apply.
Путь ожидается, например: $sdk\cmdline-tools\latest\bin
"@
    exit 1
}

Write-Host "Найден: $cmdBin"

if (Test-Path $targetBin) {
    $item = Get-Item $targetBin -Force
    $isLink = ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
    if ($isLink) {
        Write-Host "Уже есть reparse point: $targetBin"
        exit 0
    }
    Write-Host "Папка $targetBin уже существует и не junction — удалите или переименуйте её вручную, затем запустите скрипт снова."
    exit 1
}

try {
    New-Item -ItemType Junction -Path $targetBin -Target $cmdBin -Force | Out-Null
} catch {
    Write-Host "Не удалось создать junction (попробуйте PowerShell от имени администратора):"
    Write-Host $_
    Write-Host ""
    Write-Host "Вручную в cmd от администратора:"
    Write-Host "mklink /J `"$targetBin`" `"$cmdBin`""
    exit 1
}

Write-Host "OK: junction создан"
Write-Host "  $targetBin"
Write-Host "  -> $cmdBin"
Write-Host "Дальше: npx @bubblewrap/cli doctor"
