# UWB Board Programmer 2.6.0

**Current release:** double-click **START_HERE_2_6_0.cmd** after cloning or pulling this repository on Windows 10/11 x64. It verifies and extracts the included portable package and creates a versioned Desktop shortcut. Python, Qt and SDK installation are not needed to run it. BLE acquisition requires a working Windows Bluetooth LE adapter; USB flashing requires the board's driver.

Earlier launch scripts, source revisions and releases are preserved. START_HERE.cmd belongs to the older release; use the versioned entry point above for 2.6.0.

- [English guide](docs/INTEGRATED_STANDALONE_GUIDE.v8.en.md)
- [คู่มือภาษาไทย](docs/INTEGRATED_STANDALONE_GUIDE.v8.th.md)
- [RTLS connection guide](docs/RTLS_CONNECTION_2_6_0.th.md)
- [Changes and verification](docs/RELEASE_2_6_0.md)

Application source: app/revisions/v14. Desktop builder: tools/package_desktop_v14_release.py. Distribution builder: tools/build_github_distribution_v11.py. Portable verifier: tools/verify_github_distribution_v11.py. Test configuration: pytest.generic.v1.ini.

The portable ZIP includes runtime, drivers' programming utilities and seven firmware images with manifests. It excludes vendor SDK source trees, personal profiles, tokens and recordings. Firmware remains Anchor 1.4.1-pilot / Tag 1.5.1-pilot; upgrading from 2.5.0 does not require reflashing.
