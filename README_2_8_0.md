# UWB Board Programmer 2.8.0

Double-click **START_HERE_2_8_0.cmd** on Windows 10/11 x64. The complete portable runtime, BLE acquisition, programmer and firmware are included. A compatible Windows BLE adapter and USB driver are required. The launcher creates a separate **UWB Board Programmer 2.8.0** Desktop shortcut and preserves older versions.

New: **Align survey to floor** after Auto Survey, with Anchor reference, Survey Origin or paired-reference registration, yaw+translation at fixed scale 1, preview, independent checks, explicit Z convention and retained source survey. A4 can become Floor XY=(0,0) while keeping its actual Z. Repeating alignment does not accumulate offsets.

Legacy profiles start Unmapped. Confirm a Floor frame before cloud publication. The active solver, anchors, AoA orientations, map, 30-second path and payload all use Floor coordinates consistently. Site/floor or geometry changes require review. No firmware update is needed for coordinate alignment; CR2032/BLE calibration remains supported.

- [English guide](docs/INTEGRATED_STANDALONE_GUIDE.v10.en.md)
- [คู่มือภาษาไทย](docs/INTEGRATED_STANDALONE_GUIDE.v10.th.md)
- [Implementation and verification](docs/COORDINATE_ALIGNMENT_2_8_0.md)
- Source: app/revisions/v16
- Tests: pytest.coordinates.v1.ini
- Build/package: tools/package_desktop_v16_release.py and tools/build_github_distribution_v13.py
- Portable checks: tools/verify_github_distribution_v13.py

Portable archives and Git contain no personal profiles, gateway tokens or recordings. Vendor SDK source is excluded. Earlier files and RTLSSimulator are preserved. Coordinate agreement with a server is distinct from physical RF accuracy validation.
