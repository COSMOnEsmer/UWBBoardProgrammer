# Actual 2.2.1 Auto Survey backend check

Tested 4 November 2026 with the exact acquisition function used by the new GUI:
`app/revisions/v9/uwb_board_programmer/survey_workflow.py::capture_reference`.

- USB Tag: Type2DK / 1.4.2-pilot / COM9, verified before radio commands.
- Powered anchors: A1, A2, A4 / 1.4.1-pilot. A3 unpowered.
- Capture duration: 20 seconds per available anchor.
- No cached ranges, Flash or RTLS publication.

| Anchor | Records | LOS | NLOS | Failed | Range result |
|---|---:|---:|---:|---:|---|
| A1 | 127 | 126 | 0 | 1 | Accepted, median 0.94 m, 124 retained |
| A2 | 127 | 0 | 127 | 0 | Rejected: fewer than 12 LOS samples |
| A4 | 123 | 123 | 0 | 0 | Accepted, median 1.11 m, 121 retained |

This actual run demonstrated that A2's quality failure does not prevent A4
capture; valid A1/A4 ranges are retained and the returned missing list is A2/A3.
Active anchors acknowledged standalone restoration. The Tag restore completed
without exception. The firmware was not changed.

An earlier fresh 20-second run accepted A1/A2/A4 at 0.97/1.27/1.13 m, respectively.
The subsequent A2 rejection shows link-quality variability remains; increasing
capture time does not guarantee LOS or solve the underlying RF conditions.
Both results are retained. No independent Tag-to-anchor distances were supplied.

The user had moved A2 into A3's former position due to power constraints. This
is link-testing evidence, not a fixed four-anchor survey. A3 readings from earlier
arrangements were not combined to manufacture an XYZ solution. The software
still requires four measured, non-coplanar Tag reference points and fixed antenna
positions before saving a survey, followed by separate 3D accuracy validation.

Local evidence (excluded from the Git payload):

- `verification/auto-survey-app-2.2.1-20261104T002156944819Z/report.json`
- `verification/auto-survey-tag-subsets-20261104T001545108754Z/report.json`

Reproduction helper: `tools/test_auto_survey_reference_v2.py`.
