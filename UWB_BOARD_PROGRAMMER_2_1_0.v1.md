# UWB Board Programmer 2.1.0

The original full UWB Board Programmer workspace now integrates standalone
firmware and BLE/GATT. This is the current application entry point.

- Desktop: **UWB Board Programmer 2.1.0**
- Launcher: `Start_UWB_Board_Programmer_v4.cmd`
- Source: `app/revisions/v5/launch.py`
- Package builder: `tools/package_desktop_v5.py`

The workspace retains Devices & firmware, Survey & calibration, Live positioning
with the floor map and clock table, RTLS Platform, and Sessions & replay. The
added BLE/GATT page provides discovery, scan settings, UWB MAC assignment,
firmware/configuration checks, capture and connection status.

Select **Standalone BLE/GATT** or the original **USB Legacy** transport. Flash
one selected board at a time. Standalone images bind A1 master, A2–A4 slaves and
Tag identities; a selected-board backup and verification precede deployment.
Standalone Pause/Disconnect controls PC processing and reception; it does not
send STOP to the autonomous UWB radios.

The local Windows onedir package includes Python/native dependencies, resources,
DK6 and the verified firmware bundles. Move the entire package folder to another
Windows x64 PC. BLE adapter/driver and four-link acceptance still need testing
on that PC. Vendor binaries, firmware images, recordings, credentials and local
packages are excluded from this repository.

Earlier source, application releases, shortcuts, BLE Pilot and simulator files
remain preserved. No original files are overwritten.

- [Thai operating guide](docs/INTEGRATED_STANDALONE_GUIDE.v1.th.md)
- [English operating guide](docs/INTEGRATED_STANDALONE_GUIDE.v1.en.md)

Validation covers the integrated UI/controller, retained USB routing,
coordinate/clock calculations, acceptance gates and localhost RTLS. Four-anchor
RF synchronization, measured 3D accuracy, battery/Power Bank operation and
production RTLS still require physical acceptance. Software fixtures do not
establish those hardware results.

Run integrated tests with `python -m pytest -c pytest.integrated.v1.ini`.
That configuration selects the v5 package. The original root test configuration
continues to select v4; the integrated-only modules skip in that environment.
Export a local laptop ZIP with `tools/export_integrated_portable_v1.py` after
building the final package.
