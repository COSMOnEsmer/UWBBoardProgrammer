# UWB Board Programmer 2.3.1

After pulling the full repository on Windows x64, double-click
`START_HERE_2_3_1.cmd`. It verifies the bundled package, installs into a new
user-local directory and creates **UWB Board Programmer 2.3.1** on the Desktop.
Python and the Murata SDK are not required to run it. BLE needs a compatible
Windows Bluetooth LE adapter/driver; USB flashing needs the FTDI driver.

This keeps the original six-page English/Thai workspace, adds Tag 1.5.1-pilot
HPD recovery/diagnostics and starts Anchor transmission before battery Tag RX.
All Anchors remain on 1.4.1-pilot; the Tag used during development is already
flashed with the corrected 1.5.1 image.

Real CR2032 testing of the exact GUI calibration backend accepted ranges from
all four Anchors in one batch without a Tag USB cable or Reset. This establishes
the battery calibration data path, not a completed XYZ survey or 3D accuracy.
Radio restoration was acknowledged; no RTLS data was published during testing.

Next: **Survey & calibration → Auto Survey / Calibration → BLE Tag / CR2032**.
Mark and measure origin/+X/+Y/+Z Tag antenna points, keep all Anchors fixed,
capture all four reference points, review and save a new profile. Reset Tag
to reopen its 15-minute BLE control window when required.

- [Thai guide](docs/INTEGRATED_STANDALONE_GUIDE.v7.th.md)
- [English guide](docs/INTEGRATED_STANDALONE_GUIDE.v7.en.md)
- [Real hardware acceptance and remaining limits](deployment/BATTERY_FOUR_ANCHOR_CAPTURE.v3.md)

Earlier releases and RTLSSimulator remain preserved.
