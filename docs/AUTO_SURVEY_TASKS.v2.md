# Auto Survey development status — 2.2.0

Completed software and firmware work:

1. Inspected SDK TWR/UL APIs, Murata board calibration and physical identities.
2. Implemented leased BLE radio control/status/TWR records and standalone restoration.
3. Built new images in separate SDK work copies; identified/backed up/flashed all four anchors.
4. Demonstrated actual anchor-pair and USB Tag TWR with radio restoration acknowledgements.
5. Implemented LOS-only robust ranges, four-known-reference anchor trilateration,
   uncertainty/consistency checks and rejection of inadequate 3D geometry.
6. Added the bilingual Auto Survey wizard to a new revision of the full app,
   including sequential power subsets, preview and save-new-profile behavior.
7. Passed 34 regression tests and 9 portable Windows distribution checks; inspected UI.
8. Packaged all six firmware choices and the self-contained 2.2.0 app, and created
   its versioned Desktop shortcut. Git distribution assets are explicitly versioned.

The primary method was refined after real link/power tests: each anchor is located
from the Tag at four measured non-coplanar positions. Six inter-anchor links are
optional diagnostics; they need not all be LOS for the primary survey.

Remaining physical acceptance requires user placement/power switching:

- Capture all four anchors at origin, +X, +Y and +Z using independently measured axes/lengths.
- Check calculated anchor coordinates with independent measurements.
- Restore the normal battery Tag, then evaluate 3D TDoA at separate known Tag positions/heights.
- Align the measured coordinate frame to the existing RTLS floor before publishing.

A Tag at one point cannot determine the axes/unknown XYZ. Firmware/UI delivery is
not a claim of completed physical calibration, antenna-delay calibration or proven 3D accuracy.
