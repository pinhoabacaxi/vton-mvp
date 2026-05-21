$ErrorActionPreference = "Stop"

$androidSdkRoot = $env:ANDROID_SDK_ROOT
if (-not $androidSdkRoot) {
  $androidSdkRoot = "$env:LOCALAPPDATA\Android\Sdk"
}

$avdName = "Pixel_4_API_33"
$emulatorPath = "$androidSdkRoot\emulator\emulator.exe"

if (-not (Test-Path $emulatorPath)) {
  throw "Não foi possível encontrar o emulador em $emulatorPath"
}

Write-Host "Iniciando emulador $avdName..."
& $emulatorPath -avd $avdName
