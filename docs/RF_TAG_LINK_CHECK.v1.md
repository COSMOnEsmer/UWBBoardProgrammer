# USB Tag reference link check — 4 November 2026

Actual powered set: A1, A3, A4. A2 was unplugged to free a USB supply for
Type2DK. Tag identity was verified on COM9 as Type2DK / 1.4.2-pilot /
0200000000000101. Anchors advertised 1.4.1-pilot. No firmware was flashed.

The Tag remained stationary at the user's proposed origin. In the standard
reference capture, A1 returned 39 successful TWR measurements, all flagged NLOS;
the capture correctly rejected them and did not create anchor coordinates.

A separate diagnostic then measured every available anchor, preserving raw
samples even if an earlier link failed the quality gate:

| Link | Successful records | LOS | NLOS | Accepted range |
|---|---:|---:|---:|---|
| A1–Tag | 38 | 0 | 38 | Rejected |
| A3–Tag | 38 | 38 | 0 | Median 1.45 m; sample standard deviation 0.023 m |
| A4–Tag | 37 | 0 | 37 | Rejected |

NLOS is the radio's reported classification. It does not by itself identify the
physical obstruction or prove that the board is faulty. The observations show
working Tag control, BLE telemetry and TWR exchange; they do not establish a
valid four-anchor calibration or a position accuracy result.

Each anchor acknowledged return to mode 0. The Tag was also commanded back to
normal radio operation; it remains on the awake USB calibration image, not the
normal CR2032 image. No RTLS traffic was started.

Next physical step: clear the antenna paths/nearby obstructions and repeat at a
new stationary origin. **Do not merge previous ranges if the Tag or an anchor
moves.** The successful A3 range from this placement must not be carried into a
different Tag placement. After links pass, sequential-power continuation still
requires measurement of the missing A2 at the same stationary reference point.

Diagnostic tool: `tools/test_auto_survey_tag_links_v1.py` (does not change firmware
or quality thresholds). Source and portable app 2.2.0 remain unchanged.

Local raw evidence, excluded from Git:

- `verification/auto-survey-reference-20261103T212405611043Z/report.json`
- `verification/auto-survey-tag-links-20261103T212607709964Z/report.json`
