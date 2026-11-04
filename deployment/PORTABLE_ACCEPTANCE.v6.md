# 2.3.0 portable acceptance receipt

Validated 4 November 2026 (Asia/Bangkok).

- **44 regression tests passed** for the integrated desktop and BLE Tag controls.
- The isolated battery-control suite also passed **8 tests** when run separately.
- **9 portable checks passed** with no external Python on launch PATH, including
  fresh installation/reuse, six-page launch, corruption repair into a new folder,
  and rejection of traversal, unlisted files and incomplete archives.
- English/Thai battery Tag wizard screens were rendered and inspected.
- Created Desktop shortcut **UWB Board Programmer 2.3.0.lnk** through the shipped launcher.
- Packaged app starts no BLE acquisition or RTLS traffic automatically.

Payload: `deployment/windows-x64/2.3.0/UWB_Board_Programmer_2_3_0_Windows_x64.zip`

- Bytes: **95,913,592**
- SHA-256: `5c593994daf1048fc6afad4fb1ba514bd1dcd6deae168c898b445461792db6b2`
- Verified files: **573**
- Firmware choices: **7**, including the BLE Tag pilot and preserved legacy images.

Local evidence:

- `verification/github-portable-v6-20261104T011644782622Z/report.json`
- `verification/auto-survey-ui-20261104T010933091500Z/`
- `verification/installation-2.3.0-20261104T011851651646Z.json`

See `VALIDATION.v6.md` and `BATTERY_WINDOW_ACCEPTANCE.v1.md` for real CR2032/GATT/RF
evidence and limits. Software/portable checks are not a 3D accuracy or lifetime test.
All earlier releases and original project files were preserved.
