param(
    [string]$Version = "dev"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$releaseName = "VideoCropStudio-$Version-windows-x64"
$releaseRoot = Join-Path $projectRoot "release"
$releaseDir = Join-Path $releaseRoot $releaseName
$zipPath = Join-Path $releaseRoot "$releaseName.zip"

Write-Host "Installing build dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

Write-Host "Building Windows bundle..."
pyinstaller packaging/video_crop_tool.spec --noconfirm --clean

if (Test-Path $releaseDir) {
    Remove-Item -Path $releaseDir -Recurse -Force
}

if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

New-Item -ItemType Directory -Path $releaseDir | Out-Null
Copy-Item -Path "dist/VideoCropStudio/*" -Destination $releaseDir -Recurse
Copy-Item -Path "README.md" -Destination $releaseDir

$windowsReadme = @"
Video Crop Studio for Windows

1. Extract this zip file.
2. Open the extracted folder.
3. Run VideoCropStudio.exe.

Notes:
- Keep all files in the extracted folder together with the exe.
- Windows Defender may scan the app the first time you open it.
- The bundle already includes the FFmpeg binary used by the app.
"@

Set-Content -Path (Join-Path $releaseDir "README-WINDOWS.txt") -Value $windowsReadme -Encoding ASCII

Compress-Archive -Path "$releaseDir\*" -DestinationPath $zipPath -Force

Write-Host "Windows release package created at $zipPath"
