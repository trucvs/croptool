param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3.13 --version *> $null
            return @("py", "-3.13")
        } catch {
            return @("py")
        }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }

    throw "Khong tim thay Python. Can cai Python 3.13.x tren VDI truoc."
}

function Test-PythonVersion {
    param(
        [string[]]$PythonCommand
    )

    $pythonArgs = @()
    if ($PythonCommand.Length -gt 1) {
        $pythonArgs = $PythonCommand[1..($PythonCommand.Length - 1)]
    }

    $versionText = & $PythonCommand[0] @pythonArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    if (-not $versionText.StartsWith("3.13.")) {
        throw "Can Python 3.13.x de cai wheel offline. Dang tim thay $versionText."
    }
}

$pythonCmd = Get-PythonCommand
Test-PythonVersion -PythonCommand $pythonCmd

$pythonArgs = @()
if ($pythonCmd.Length -gt 1) {
    $pythonArgs = $pythonCmd[1..($pythonCmd.Length - 1)]
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Tao virtual environment..."
    & $pythonCmd[0] @pythonArgs -m venv .venv
}

$stampFile = Join-Path $root ".venv\.deps_installed"
if (-not (Test-Path $stampFile)) {
    Write-Host "Cai dependencies offline tu wheelhouse..."
    & $venvPython -m pip install --no-index --find-links wheelhouse -r requirements.txt
    Set-Content -Path $stampFile -Value "ok" -Encoding ASCII
}

Write-Host "Khoi dong Video Crop Studio..."
& $venvPython video_crop_tool.py
