@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0build_vdi_bundle.ps1"
