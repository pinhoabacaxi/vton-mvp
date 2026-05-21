$ErrorActionPreference = "Stop"

$androidSdkRoot = "$env:LOCALAPPDATA\Android\Sdk"
$cmdlineZip = "$env:TEMP\commandlinetools.zip"
$cmdlineRoot = "$androidSdkRoot\cmdline-tools\latest"

if (-Not (Test-Path $androidSdkRoot)) {
    New-Item -ItemType Directory -Path $androidSdkRoot | Out-Null
}

Write-Host "Baixando Android Command Line Tools..."
Invoke-WebRequest -Uri "https://dl.google.com/android/repository/commandlinetools-win-9477386_latest.zip" -OutFile $cmdlineZip

Write-Host "Extraindo para $cmdlineRoot..."
if (Test-Path $cmdlineRoot) {
    Remove-Item -Recurse -Force $cmdlineRoot
}
Expand-Archive -Path $cmdlineZip -DestinationPath "$androidSdkRoot\cmdline-tools" -Force
Rename-Item -Path "$androidSdkRoot\cmdline-tools\cmdline-tools" -NewName "latest" -Force

Write-Host "Instalando plataforma Android e ferramentas de build..."
$env:ANDROID_SDK_ROOT = $androidSdkRoot
$toolsBin = "$cmdlineRoot\bin"
& "$toolsBin\sdkmanager.bat" --sdk_root="$androidSdkRoot" "platform-tools" "platforms;android-33" "build-tools;33.0.2" "cmdline-tools;latest"

Write-Host "Configuração concluída. Adicione as variáveis de ambiente se necessário:"
Write-Host "  ANDROID_SDK_ROOT=$androidSdkRoot"
Write-Host "  PATH+=${androidSdkRoot}\platform-tools;${androidSdkRoot}\cmdline-tools\latest\bin"
