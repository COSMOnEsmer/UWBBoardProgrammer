# UWB Board Programmer 2.7.0

Run **START_HERE_2_7_0.cmd** on Windows 10/11 x64. The included portable package contains Python/Qt, BLE acquisition, programming utilities and firmware. A compatible Windows BLE adapter and the board's USB driver are still required. The launcher creates a **UWB Board Programmer 2.7.0** Desktop shortcut. Older scripts and versions are preserved.

This release redesigns all six workflows around readable dock panels: full-width anchor geometry, a larger live map, compact coordinate readouts, collapsed advanced settings and a quiet log footer. Drag panel dividers to resize, drag section headings to dock elsewhere, and use **Open window / Attach** to float and return live controls. Small screens scroll the whole page instead of clipping forms.

- [English guide](docs/INTEGRATED_STANDALONE_GUIDE.v9.en.md)
- [คู่มือภาษาไทย](docs/INTEGRATED_STANDALONE_GUIDE.v9.th.md)
- [Design and verification notes](docs/design-v15/DESIGN.md)

Active source: app/revisions/v15. Tests: pytest.design.v1.ini. Builder: tools/package_desktop_v15_release.py. Distribution builder/verifier: tools/build_github_distribution_v12.py and tools/verify_github_distribution_v12.py.

Firmware, RF processing, 30-second paths, strict cloud publishing and credentials remain as in 2.6.0. Upgrading the desktop application does not require reflashing. Profiles and encrypted credentials migrate into a new installation directory. Personal data is excluded from the Git payload. RTLSSimulator and earlier files are preserved.
