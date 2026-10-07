@echo off
setlocal
set "UWB_BOARD_PROGRAMMER_ROOT=%~dp0"
set "UWB_LAUNCH_EXE=%~dp0releases\desktop-v3\UWB_Board_Programmer\UWB_Board_Programmer.exe"
if not exist "%UWB_LAUNCH_EXE%" goto source
start "" /D "%~dp0" "%UWB_LAUNCH_EXE%"
exit /b 0
:source
if not exist "%~dp0runtime\python-v1\Scripts\pythonw.exe" goto missing
start "" /D "%~dp0" "%~dp0runtime\python-v1\Scripts\pythonw.exe" "%~dp0app\revisions\v4\launch.py"
exit /b 0
:missing
echo UWB Board Programmer has not been built on this computer.
echo See docs\BUILD_EN.v2.md for setup and packaging instructions.
pause
exit /b 1
