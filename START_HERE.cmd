@echo off
setlocal
cd /d "%~dp0"
start "" /D "%~dp0" "%~dp0deployment\windows-x64\UWB_Board_Programmer_Launcher.exe" --root "%~dp0."
