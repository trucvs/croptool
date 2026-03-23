@echo off
setlocal
set VERSION=%1
if "%VERSION%"=="" set VERSION=dev
powershell -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1" -Version "%VERSION%"
