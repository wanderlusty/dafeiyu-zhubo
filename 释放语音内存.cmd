@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0workspaces\operations\释放语音内存.ps1"
if errorlevel 1 pause
