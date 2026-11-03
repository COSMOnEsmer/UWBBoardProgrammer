# Version 2.2.0 validation

New source revision: `app/revisions/v8`. Earlier releases, source revisions,
profiles, firmware and RTLSSimulator were preserved. All new reports use unique paths.

## Checks completed before packaging

- 34 automated tests passed: Auto Survey protocol CRC/request binding, leased
  command constraints, LOS-only robust ranges, geometry rejection, four known
  non-coplanar Tag reference points, sequential power subsets, save-new profiles,
  previous clock recovery and position rejection diagnostics, and six-page UI.
- Complete mixed-version six-image bundle: four anchors **1.4.1-pilot**, USB
  calibration Tag **1.4.2-pilot**, preserved normal battery Tag **1.3.4-pilot**.
  Every image passed SHA-256, boot-header/vector checksum and provisioning CRC checks.
- All four Rev4.1 anchors were identified, backed up twice, flashed, byte-verified,
  and acknowledged the correct model/MAC/version/CRC. No OTP was written.
- A1–A2 TWR: typical median **1.55–1.56 m**; user's independent tape estimate
  **1.5–1.55 m**. This one baseline does not validate full 3D accuracy.
- A1–Type2DK USB TWR: **51 LOS samples, median 0.99 m**, acknowledged return to
  standalone operation. No independent distance was supplied for this placement.
- Latest actual six-pair diagnostic (all four anchors powered): four accepted
  links, two insufficient-LOS links. A1–A2 1.560 m, A1–A3 1.890 m, A1–A4 1.105 m,
  A2–A3 1.440 m. A2–A4 and A3–A4 were rejected for insufficient LOS samples.
  All four anchors acknowledged mode 0 restoration. Full six-edge geometry was
  therefore not accepted or used to invent coordinates.
- Windows BLE ATT write/read timeouts were increased to 8 seconds based on real
  link traces; notification shutdown and restoration are serialized. Firmware
  leases remain the fallback if explicit restoration cannot be acknowledged.

Local raw evidence, intentionally excluded from Git distribution:

- `verification/auto-survey-restore-trace-20261103T200545844260Z/report.json`
- `verification/auto-survey-real-tag-20261103T202836249832Z/report.json`
- `verification/auto-survey-links-20261103T205659211105Z/report.json`
- `verification/flash-jobs/` and `verification/host-backups/` (same-board backups).

## Acceptance still requiring physical measurements

The primary workflow trilaterates each anchor from distances to the Tag at four
physically known non-coplanar locations. Synthetic tests of this method are not
physical calibration evidence. A complete physical four-reference capture and
holdout Tag positions/heights must still be measured. Unknown antenna delay,
reference-placement errors, NLOS and TDoA clock/timestamp noise can still limit
accuracy. A four-anchor planar or nearly planar installation is unsuitable for
reliable unrestricted 3D TDoA and is rejected where the model exposes that defect.

The reference lengths/axes are training inputs, not independent holdout checks.
No TDoA uncertainty gates were weakened and no RF positions were fabricated.
No RTLS traffic was initiated by the hardware/calibration verification scripts.
The new survey frame must be aligned with the existing RTLS map before publishing.

## Portable Windows distribution

Build tools: `package_desktop_v8.py`, `build_github_distribution_v4.py`.
Launcher: `Bootstrap.v4.cs`, manifest `distribution.v4.json`.
Start command: `START_HERE_2_2_0.cmd`. Every distributed file is hashed.
The distribution embeds Python/Qt/BLE dependencies, programmer and firmware;
vendor SDK trees, local recordings, credentials and backups are excluded.
The portable verifier exercises installation, reuse, launch without Python on
PATH, corruption repair without overwrite, archive traversal/unlisted-file
rejection and incomplete-download rejection. Results are recorded separately.
