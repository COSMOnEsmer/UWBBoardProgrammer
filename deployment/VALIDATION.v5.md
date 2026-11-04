# Version 2.2.1 validation and RF evidence

New source: `app/revisions/v9`. Published 2.2.0 files are preserved; all edits are
in new revision paths. Firmware is the same verified six-image bundle used by 2.2.0.

## Application changes

Auto Survey capture duration is selectable from 5 to 20 seconds, default 20.
Capture records include per-anchor LOS/NLOS/failure counts. Range-quality rejection
continues to the next available anchor, retaining valid stationary-point ranges;
transport or unacknowledged radio restoration still stops the operation. Existing
LOS, consistency, geometry and position uncertainty acceptance criteria remain unchanged.

The wizard requires confirmation of marked, fixed antenna positions. It explains
that calibration can run with only one powered anchor and the USB Tag, by moving
the power supply/cable between fixed anchors. Normal live 3D TDoA still requires
four powered anchors simultaneously. BLE/GATT does not require anchor USB data cables.

## Actual link tests, 4 November 2026

The user moved A2 to A3's former position because of limited power connections.
A3 was then unpowered. Earlier A3 measurements were not merged into the resulting
installation. The tests below are link diagnostics, not a four-anchor survey.

At an earlier, user-selected Tag placement, fresh 5-second captures accepted:
A3 1.43 m (39 LOS, 36 retained), A4 2.77 m (37 LOS); A1 was rejected for 0 LOS/37.
After A2 replaced A3, a 5-second run accepted A2 1.44 m (37 LOS); A1/A4 failed quality.

A subsequent 20-second run accepted A1 0.98 m and A4 1.13 m. These differed
substantially from earlier observations, so a **fresh set without cached ranges**
was collected rather than treating the earlier ranges as one verified geometry:

| Link | Records | LOS | NLOS | Failed | Retained LOS | Median range | Sample std |
|---|---:|---:|---:|---:|---:|---:|---:|
| A1–Tag | 126 | 126 | 0 | 0 | 121 | 0.97 m | 0.0191 m |
| A2–Tag | 115 | 55 | 59 | 1 | 54 | 1.27 m | 0.0524 m |
| A4–Tag | 127 | 127 | 0 | 0 | 126 | 1.13 m | 0.0209 m |

Every active anchor acknowledged standalone mode 0 restoration. The USB Tag also
acknowledged its restore command. No firmware was flashed or RTLS data published.
NLOS is the radio's classification, not proof of a particular obstruction.
The observations do not isolate the cause of the changed ranges or establish
that longer capture duration alone caused improvement. No independent tape/laser
distances were provided for these Tag placements, so accuracy is not proven.

Local evidence (not distributed):

- `verification/auto-survey-tag-links-20261103T234748015044Z/report.json`
- `verification/auto-survey-tag-links-20261104T001057072728Z/report.json`
- `verification/auto-survey-tag-subsets-20261104T001318402283Z/report.json`
- `verification/auto-survey-tag-subsets-20261104T001545108754Z/report.json`

## Required physical acceptance

Choose four distinct, fixed installation positions with useful height diversity.
Mark the antenna positions. Capture Tag at physically measured origin/+X/+Y/+Z,
powering anchors sequentially if needed. Validate calculated coordinates and later
3D TDoA at separate known positions/heights. Align the survey frame to the RTLS map
before publishing. No complete physical four-reference or 3D accuracy acceptance
is claimed by this release.

## Distribution checks

New build tools: `package_desktop_v9.py`, `build_github_distribution_v5.py`,
`verify_github_distribution_v5.py`. New launcher and manifest use v5 names.
The separate portable acceptance receipt records the actual package hash/checks.
The package contains no local board backups, measurement sessions or credentials.
