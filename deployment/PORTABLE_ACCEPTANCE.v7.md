# 2.3.1 portable Windows x64 acceptance

The package contains Python, Qt, BLE/WinRT dependencies, compiled firmware and
DK6 tools. Runtime use does not require a Python or Murata SDK installation.
Bluetooth LE/FTDI drivers and compatible Windows hardware remain prerequisites.

- ZIP: `windows-x64/2.3.1/UWB_Board_Programmer_2_3_1_Windows_x64.zip`.
- Size: 95,941,055 bytes; 576 verified files.
- SHA-256: `d9022d8ddef6a6bd995d2fd9251bd415016b3385c354ba06bdbe804e652a3291`.
- Entry: `START_HERE_2_3_1.cmd`, launcher v7, distribution manifest v7.

Nine checks passed from a new disposable checkout with Thai characters/spaces
and a PATH containing only Windows system directories: archive verification,
first install, reuse, actual packaged application launch, repair while preserving
the damaged copy, reuse repaired install, and rejection of traversal, unexpected
files and an incomplete payload. The actual program reported 2.3.1, six pages,
four anchor rows, five device rows and no automatic acquisition/cloud connection.

Receipt: `verification/github-portable-v7-20261104T022130167164Z/report.json`.

The verified package was separately prepared in a new user-local installation
and a new Desktop shortcut **UWB Board Programmer 2.3.1** was created. Earlier
installations/shortcuts were preserved. Installation receipt:
`verification/installation-2.3.1-20261104T022152268369Z.json`.

No credentials, user profiles or hardware recordings are included. These checks
do not establish BLE driver/radio performance on every laptop. Hardware control
and remaining survey limitations are recorded in BATTERY_FOUR_ANCHOR_CAPTURE.v3.md.
