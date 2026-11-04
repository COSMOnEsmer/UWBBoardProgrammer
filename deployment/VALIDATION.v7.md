# 2.3.1 validation scope

Application source: `app/revisions/v11`; BLE Tag control/capture:
`app/battery_calibration/v2`; firmware source:
`firmware/source/v25-battery-radio-recovery`.

42 regression tests passed in the new desktop configuration. Ten native C
fault-injection scenarios passed against the actual radio lifecycle functions,
with an independent diagnostic CRC check. English/Thai wizard screenshots were
rendered and inspected. Nine portable launcher checks passed on the packaged
application without Python/SDK in PATH. Earlier files and RTLSSimulator are preserved.

The identified Type2DK was backed up, flashed and byte-verified as 1.5.1-pilot.
Deliberate HPD wake recovery was observed on real hardware. After changing the
PC startup order to Anchor-first, repeated A4 and A3 measurements recovered on
CR2032 without another Tag Reset. The exact GUI backend subsequently returned
all four accepted Anchor ranges in one batch with no failed RF records, missing
anchors or acquisition errors. No Tag USB or serial connection was used.

The finite Tag BLE window then closed while common BLINK reception continued
at all four anchors. This is observable RF continuity, not an electrical current
or battery-lifetime measurement.

Evidence and precise limitations:

- [Hardware batch and recovery](BATTERY_FOUR_ANCHOR_CAPTURE.v3.md)
- [BLE window and RF continuity](BATTERY_WINDOW_ACCEPTANCE.v2.md)
- [Portable installation/launch](PORTABLE_ACCEPTANCE.v7.md)

Not yet accepted: four physically measured Tag reference points, resulting
Anchor XYZ, independent 3D positioning accuracy, RTLS frame alignment/publishing,
low-battery behavior and current/lifetime. The diagnostic batch's zero label is
not a surveyed origin and was not used to produce a position or profile.
