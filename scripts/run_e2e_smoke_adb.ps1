#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

# E2E smoke script using adb. Saves artifacts to C:\Dev\AI\logs
$package = "com.anonymous.vtonmvp"
$activity = ".MainActivity"
$logDir = "C:\Dev\AI\logs"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Write-Host "E2E smoke test started at $ts"

# locate adb: prefer PATH, fallback to common SDK location
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if ($null -ne $adbCmd) {
    $adb = $adbCmd.Path
} else {
    $adbFallback = 'C:\Users\rafae\AppData\Local\Android\Sdk\platform-tools\adb.exe'
    if (Test-Path $adbFallback) {
        $adb = $adbFallback
    } else {
        Write-Error "adb not found in PATH or at $adbFallback. Ensure Android SDK platform-tools installed."
        exit 2
    }
}

$devices = & $adb devices | Select-Object -Skip 1 | Where-Object { $_ -match '\S' } | ForEach-Object { ($_ -split '\s+')[0] }
if ($devices.Count -eq 0) {
    Write-Warning "No adb devices found. The emulator must be running and visible to adb."
} else {
    Write-Host "Found adb devices: $($devices -join ', ')"
}

Write-Host "Clearing logcat"
& $adb logcat -c

Write-Host "Starting app $package/$activity"
& $adb shell am start -n "$package/$activity" | Out-Null
Start-Sleep -Seconds 4

# Dump UI hierarchy
$deviceDump = "/sdcard/window_dump_$ts.xml"
$localDump = Join-Path $logDir "window_dump_$ts.xml"
Write-Host "Dumping UI hierarchy to $localDump"
try {
    & $adb shell uiautomator dump $deviceDump | Out-Null
    & $adb pull $deviceDump $localDump | Out-Null
    & $adb shell rm $deviceDump | Out-Null
} catch {
    Write-Warning "uiautomator dump/pull failed: $_"
}

# Pre-run screenshot
$deviceScreenBefore = "/sdcard/screen_before_$ts.png"
$localScreenBefore = Join-Path $logDir "screen_before_$ts.png"
try {
    & $adb shell screencap -p $deviceScreenBefore
    & $adb pull $deviceScreenBefore $localScreenBefore | Out-Null
    & $adb shell rm $deviceScreenBefore | Out-Null
    Write-Host "Saved screenshot: $localScreenBefore"
} catch {
    Write-Warning "Pre screenshot failed: $_"
}

# Run monkey to exercise the UI
$monkeyFile = Join-Path $logDir "monkey_output_$ts.txt"
Write-Host "Running monkey to exercise UI (30 events). Output -> $monkeyFile"
try {
    & $adb shell monkey -p $package --ignore-crashes --ignore-timeouts --monitor-native-crashes --throttle 300 30 2>&1 | Out-File -FilePath $monkeyFile -Encoding utf8
} catch {
    Write-Warning "Monkey run failed: $_"
}

Start-Sleep -Seconds 2

# Post-run screenshot
$deviceScreenAfter = "/sdcard/screen_after_$ts.png"
$localScreenAfter = Join-Path $logDir "screen_after_$ts.png"
try {
    & $adb shell screencap -p $deviceScreenAfter
    & $adb pull $deviceScreenAfter $localScreenAfter | Out-Null
    & $adb shell rm $deviceScreenAfter | Out-Null
    Write-Host "Saved screenshot: $localScreenAfter"
} catch {
    Write-Warning "Post screenshot failed: $_"
}

# Dump logcat to file
$logcatFile = Join-Path $logDir "e2e_log_$ts.log"
Write-Host "Dumping logcat to $logcatFile"
try {
    & $adb logcat -d -v time | Out-File -FilePath $logcatFile -Encoding utf8
} catch {
    Write-Warning "Failed to dump logcat: $_"
}

Write-Host "`nE2E artifacts saved to $logDir (matching $ts):"
Get-ChildItem -Path $logDir -Filter "*$ts*" | ForEach-Object { Write-Host $_.FullName }

Write-Host "E2E smoke test finished at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
exit 0
