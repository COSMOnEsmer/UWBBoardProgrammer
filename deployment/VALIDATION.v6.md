# 2.3.0 validation scope

All application/firmware changes are new revision paths. Previous published
releases, images and RTLSSimulator were preserved.

## Verified hardware and control path

- New Type2DK 1.5.0-pilot source `firmware/source/v24-battery-calibration-ble`.
  Built in a fresh SR040 SDK copy. Image: 446,148 bytes, SHA-256
  `455457c12f5f15fd0bec2e6c9850738e3d22cd985d628a06adbbe386438ae8da`.
- Tag identified as Type2DK / 0200000000000101 before Flash. Two matching host
  backups were taken; programmed bytes and model/version/configuration were verified.
  No OTP/protected-tail write. Local Flash report:
  `verification/flash-jobs/20261104T005335048988Z/report.json`.
- USB-powered first test connected Tag GATT, commanded responder mode, received
  125 successful TWR records and restored both radios. Only one record was LOS,
  so range quality correctly failed. No calibration fix was fabricated.
- The user then confirmed Tag USB unplugged, CR2032 selected, Reset performed,
  and all four anchors powered. BLE-only TWR with A1 accepted median **0.83 m**
  (122 retained samples), followed by A2 **1.36 m** (114 retained samples).
  Restoration was acknowledged. No Tag serial port was opened.
- A2 test used three simultaneous links: Tag, A1 and A2. The other slaves remained
  powered. This confirms the control architecture does not require five GATT links.
- After ranging, all four anchors received common Tag BLINK frames during ongoing
  observation. BLE window closure/RF continuity has a separate observation receipt;
  this is not a direct measurement of sleep current.

Local battery test evidence (excluded from distribution):

- `verification/battery-tag-pair-20261104T005910024457Z/report.json`
- `verification/battery-tag-pair-20261104T010053507407Z/report.json`

Power source was confirmed by the operator; the application does not measure the
coin-cell voltage or detect the slide-switch position through GATT.

## Software checks

**44 tests passed** covering prior clock/position/geometry behavior, BLE Tag
identity and CRC checks, lease/window guarding, no false restore after disconnect,
bounded connection count, capture error handling and a wizard that starts BLE
capture without a COM port. English/Thai screens were rendered and inspected.

New desktop source: `app/revisions/v10`. BLE Tag control/capture:
`app/battery_calibration/v1`. Existing anchors stay on 1.4.1-pilot. Seven-image
bundle adds the Tag pilot while preserving USB calibration and normal battery
images. Earlier applications still select their previous six-image bundle.

## Remaining acceptance

BLE Tag support is a pilot. The firmware holds the host awake during the finite
control window and requests power-down after BLE shutdown; actual current,
battery lifetime, low-battery/brownout behavior and exact MCU sleep state need
independent measurement. Successful RF on one coin cell does not prove lifetime.

Full physical Auto Survey needs four measured, non-coplanar Tag reference points
and fixed antenna positions. Tag BLE control does not remove those observability
requirements, calibrate unknown antenna delays, or establish 3D accuracy. Use
independent holdout positions/heights and align coordinates to the RTLS floor
before publishing. No RTLS traffic was initiated by these tests.
