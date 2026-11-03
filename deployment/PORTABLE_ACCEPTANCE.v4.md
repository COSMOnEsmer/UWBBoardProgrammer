# 2.2.0 portable acceptance receipt

Validated on Windows x64, 4 November 2026 (Asia/Bangkok).

- 34 source regression tests passed.
- 9 portable checks passed in a fresh path containing Thai text and spaces,
  with Python removed from the launch PATH.
- Packaged app opened all six pages; no automatic BLE acquisition or cloud traffic.
- Installation reuse, repair into a new folder without overwriting the damaged
  installation, traversal/unlisted-file rejection and incomplete ZIP rejection passed.
- English and Thai Auto Survey screens were rendered and visually inspected.
- Desktop shortcut **UWB Board Programmer 2.2.0.lnk** was created using the shipped
  launcher. Previous shortcuts/installations were preserved.

Payload: `deployment/windows-x64/2.2.0/UWB_Board_Programmer_2_2_0_Windows_x64.zip`

- Bytes: **95,517,359**
- SHA-256: `cb12a9a1e5e06e676aaee22fc3190023d16762e4b87fa7a3b2d869ee70108d24`
- Verified distribution files: **564**
- External Python/SDK required to run: **no**
- Compatible Windows BLE adapter/driver required for BLE: **yes**
- FTDI driver required for USB Flash: **yes**

Local evidence:

- `verification/github-portable-v4-20261103T210623521444Z/report.json`
- `verification/auto-survey-ui-20261103T210346072599Z/`
- `verification/installation-2.2.0-20261103T210700237447Z.json`

See `VALIDATION.v4.md` for actual RF evidence and the remaining physical
four-reference/3D accuracy acceptance. Portable/UI tests do not establish RF accuracy.
