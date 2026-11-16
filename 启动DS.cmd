@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0workspaces\operations\Start-DS.ps1"
if errorlevel 1 pause
