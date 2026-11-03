# Version 2.1.1 validation — 2026-11-04 (Asia/Bangkok)

Distribution SHA-256:
`8ab0461f9d312f057481e5acc0f3d21e785fb0a1b2c89f56c2c5dc57173e5193`

The Windows x64 ZIP contains 557 verified files and is 95,415,591 bytes.
All original application/distribution files are preserved. Firmware remains 1.3.4-pilot.

- **21 numerical/UI tests passed.** Includes exact large-integer timestamp handling,
  no extrapolation, invalid/stale clock rejection, boot-domain reset, retention
  across BLE transport loss, a known synthetic 3D case, unverified-survey blocking,
  the full six-page workspace, English/Thai, original USB controller selection,
  single-board Flash dispatch and credential-loader retention.
- **Nine portable-launch/integrity checks passed.** A fresh folder with Thai
  characters/spaces launched the complete package with only Windows on PATH.
  Runtime reuse, non-overwriting repair and rejection of incomplete payloads,
  archive traversal and unlisted files were checked.
- **Real four-anchor bench reception tested for 65 seconds.** All four physical
  anchors connected, each slave accumulated up to 16 SYNC samples, and all three
  clock models passed validation in 48 of 65 one-second snapshots. Initial
  connection/warm-up snapshots are included in that denominator. Other snapshots
  remained drifting when freshness/sample/validation limits were not satisfied.
- **No XYZ was generated and no RTLS connection was made during the bench test.**
  The user confirmed that the earlier survey coordinates were trial values and
  that the boards were close together. Bench diagnostics explicitly assume zero
  propagation and measure model stability only. They do not certify absolute
  synchronization, surveyed distances, actual 3D accuracy or RTLS delivery.
- An immutable snapshot of the user's real recording also reproduced the old
  repeated-reset problem and verified the revised clock diagnostic path. Local
  recordings, board identifiers and profiles are not included in this repository.

BLE transport loss is still visible in logs; this update does not claim to
eliminate its RF/transport cause. Actual 3D acceptance still requires measured,
non-coplanar anchor coordinates and reference Tag positions.
