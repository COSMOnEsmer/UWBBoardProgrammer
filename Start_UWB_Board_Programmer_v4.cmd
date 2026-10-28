@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0releases\desktop-v5\UWB_Board_Programmer_2_1_0\UWB_Board_Programmer_2_1_0.exe" (
  start "" /D "%~dp0" "%~dp0releases\desktop-v5\UWB_Board_Programmer_2_1_0\UWB_Board_Programmer_2_1_0.exe" --workspace "%~dp0."
) else (
  start "" /D "%~dp0" "%~dp0runtime\python-v1\Scripts\pythonw.exe" "%~dp0app\revisions\v5\launch.py" --workspace "%~dp0."
)
