# UWB Board Programmer — Build guide

## Desktop application

Windows 10/11 x64 and Python 3.12 x64 are the supported development setup for this release. From the project directory, create a new environment and install the pinned dependencies:

```powershell
py -3.12 -m venv runtime\python-v1
& .\runtime\python-v1\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
& .\runtime\python-v1\Scripts\python.exe -m pytest --basetemp verification\pytest-new-run
$env:PYTHONPATH = "$PWD\app\revisions\v3"
& .\runtime\python-v1\Scripts\python.exe .\app\revisions\v3\launch.py
& .\runtime\python-v1\Scripts\python.exe .\tools\package_desktop_v2.py
```

Choose an unused `--basetemp` path for every test run: pytest can replace an existing basetemp. The packaging script also refuses existing output directories. For a later build, make a new packaging script/release number instead of overwriting this release. `Start_UWB_Board_Programmer.cmd` prefers the packaged EXE and can fall back to the local Python environment.

The build uses a limited PATH so another Qt/Poppler installation cannot contribute incompatible DLLs. The program finds its workspace by `programmer-workspace.json`. Keep `resources/`, the marker and local folders with the packaged release. `UWB_BOARD_PROGRAMMER_ROOT` can explicitly point at the workspace.

The app can open from a Git checkout without vendor inputs. Firmware deployment then requires the local programmer and a complete firmware bundle. GUI startup does not automatically open a COM port or connect to the cloud.

## Locally licensed firmware inputs

These inputs are already copied into the prepared PC workspace and are intentionally excluded from the Git repository:

| Local path | Input |
| --- | --- |
| `vendor/originals/sr150/uwbiot-top/` | NXP/Murata SR150 SDK 04.06.05, Type2BP / RhodesV4_SE |
| `vendor/originals/sr040/uwbiot-top/` | NXP/Murata SR040 SDK 04.03.14, Type2DK / FinderV3 |
| `vendor/patches/2bp_prebuilt_v04.06.05.patch` | Matching Murata Type2BP patch |
| `vendor/patches/2dk_prebuilt_v04.03.14.patch` | Matching Murata Type2DK patch |
| `tools/dk6/DK6Programmer.exe` and adjacent DLLs | Vendor USB programmer |
| `tools/arm-gcc-10.3-2021.10/.../bin/arm-none-eabi-gcc.exe` | GNU Arm Embedded compiler 10.3-2021.10 |

The SDKs include the QN9090 host/RTOS board support (SDK 2.6.16). Preserve the supplied directory structure, `.cproject` settings, libraries, scripts and linker files. Do not place user credentials in source files.

```powershell
& .\runtime\python-v1\Scripts\python.exe .\tools\build_firmware_v1.py
```

Each image is built in a fresh SDK copy under `firmware/work/`. Vendor originals remain unchanged. The tool creates Master, Slave, Tag setup and Tag battery images, applies the matching vendor patch, installs the custom host code, links, updates the DK6 image header and writes SHA-256 manifests to a new timestamped `firmware/releases/` folder. The same Master/Slave pair serves both three-anchor hybrid and four-anchor TDoA modes. The firmware HELLO version is 1.0.0; the PC application version is 2.0.0.

The UART wire commands keep their existing `E2E` prefix to remain compatible with the firmware protocol; application/package/window names use UWB Board Programmer. Do not rename those commands without changing both host and firmware together.

## Verification and distribution

`tools/verify_ui_v2.py` captures all five pages in both language/topology combinations in an isolated workspace. It refuses an existing verification directory. The EXE's `--smoke-output` flag runs an explicit software numerical fixture and saves a report; it never opens serial readers or publishes that fixture to RTLS.

Local executable packages, SDKs, generated firmware, compiler, programmer, encrypted credentials, recordings and configuration files are ignored by Git. The repository is a source distribution; vendor inputs must be obtained through their authorized channels before rebuilding firmware on another PC. This project has no additional license declaration for the vendor materials.
