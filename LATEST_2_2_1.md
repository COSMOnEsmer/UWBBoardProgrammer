# UWB Board Programmer 2.2.1

Open **START_HERE_2_2_1.cmd** after a complete pull. The launcher creates the
**UWB Board Programmer 2.2.1** Desktop shortcut; previous releases are preserved.

Auto Survey now provides:

- Per-anchor capture duration **5–20 seconds**, default **20 seconds**.
- Per-anchor LOS, NLOS and failed measurement counts, with quality rejection reasons.
- Continued capture of other anchors after a quality failure; transport/restoration
  failures still stop acquisition.
- Explicit confirmation that all antennas remain at their marked installation positions.
- Sequential power: **one powered Anchor plus the USB calibration Tag is enough**
  to accumulate ranges at each stationary Tag reference point. Move the Power Bank
  or cable between anchors, preserving every antenna position.

Firmware choices are the existing tested images: anchors 1.4.1-pilot, USB calibration
Tag 1.4.2-pilot, normal battery Tag 1.3.4-pilot. The new PC controls use the existing
leased firmware protocol. No positioning or range-quality thresholds were relaxed.

- [คู่มือภาษาไทย](docs/INTEGRATED_STANDALONE_GUIDE.v5.th.md)
- [English guide](docs/INTEGRATED_STANDALONE_GUIDE.v5.en.md)
- [Actual hardware evidence and limitations](deployment/VALIDATION.v5.md)

Four measured, non-coplanar Tag reference positions are still required. Captures
from different antenna arrangements must not be combined. Full physical Auto Survey
and held-out 3D TDoA accuracy are separate acceptance work, not established by link tests.
