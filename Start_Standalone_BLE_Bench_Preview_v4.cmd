@echo off
setlocal
cd /d "%~dp0"
start "" /D "%~dp0" "%~dp0runtime\python-v1\Scripts\pythonw.exe" "%~dp0tools\launch_ble_bench_v6.py"
