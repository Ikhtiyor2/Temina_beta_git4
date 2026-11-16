# Обновление приложения: installDebug через Gradle (нужны adb и подключённое устройство).
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$androidDir = Join-Path $PSScriptRoot 'temina-android'
Set-Location $androidDir
if (-not (Test-Path '.\gradlew.bat')) {
    throw "Не найден gradlew.bat в $androidDir"
}

& .\gradlew.bat ':app:installDebug' '--no-daemon'
exit $LASTEXITCODE
