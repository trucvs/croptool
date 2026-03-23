param(
    [string]$PythonVersion = "3.13",
    [string]$BundleName = "VideoCropStudio-source-vdi-py313"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Khong tim thay .venv\Scripts\python.exe. Hay tao .venv va cai dependencies truoc."
}

$wheelhouseDir = Join-Path $projectRoot "wheelhouse"
$stagingRoot = Join-Path $projectRoot "build"
$stagingDir = Join-Path $stagingRoot "${BundleName}-staging"
$zipPath = Join-Path $PSScriptRoot "$BundleName.zip"

Write-Host "Refreshing offline wheelhouse..."
& $pythonExe -m pip download -r requirements.txt -d $wheelhouseDir

if (Test-Path $stagingDir) {
    Remove-Item -Path $stagingDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingDir | Out-Null

Write-Host "Copying bundle contents..."
Copy-Item -Path "croptool" -Destination $stagingDir -Recurse
Copy-Item -Path "wheelhouse" -Destination $stagingDir -Recurse
Copy-Item -Path "video_crop_tool.py","requirements.txt","README.md","README-VDI.txt","run_on_vdi.ps1","run_on_vdi.bat" -Destination $stagingDir

Get-ChildItem -Path $stagingDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $stagingDir -Recurse -File -Include "*.pyc","*.pyo","*.pyd" | Remove-Item -Force

if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

Write-Host "Creating VDI bundle zip at $zipPath"
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath -Force

Write-Host "VDI bundle created at $zipPath"
