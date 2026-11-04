# 2.2.1 portable acceptance receipt

Validated on Windows x64, 4 November 2026 (Asia/Bangkok).

- **36 regression tests passed**, including quality-failure continuation,
  stopping on unacknowledged restoration, adjustable capture duration, fixed
  position confirmation, save-new profiles, and previous clock/position/UI behavior.
- **9 portable checks passed** with a fresh Thai/spaces path and no Python on
  launch PATH: integrity, first/repeated installation, six-page launch, repair
  without overwriting a damaged installation, and invalid-archive rejection.
- The packaged application opened six pages without automatic BLE or RTLS traffic.
- Final English/Thai Auto Survey screens were rendered and visually inspected.
- Exact new acquisition backend was tested with the connected Tag and A1/A2/A4;
  see `RF_BACKEND_ACCEPTANCE.v1.md` for results, including A2's quality rejection.

Payload: `deployment/windows-x64/2.2.1/UWB_Board_Programmer_2_2_1_Windows_x64.zip`

- Bytes: **95,544,327**
- SHA-256: `c03c4428d00a2e1f61df1a1452188d986895f56e3916ab5c2d1021f2b9f0fa55`
- Verified files: **569**
- External Python/SDK required to run: **no**
- Compatible Windows BLE adapter/driver and USB programming driver still required.

Local evidence:

- `verification/github-portable-v5-20261104T002544742181Z/report.json`
- `verification/auto-survey-ui-20261104T002234028365Z/`
- `verification/auto-survey-app-2.2.1-20261104T002156944819Z/report.json`

All published 2.2.0 and earlier source, firmware and distribution files are
preserved. These tests do not establish completed physical Auto Survey or 3D accuracy.
