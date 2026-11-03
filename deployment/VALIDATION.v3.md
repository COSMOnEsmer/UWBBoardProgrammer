# UWB Board Programmer 2.1.2 validation

Validated 4 November 2026 (Asia/Bangkok).

- 26 regression tests passed using `pytest.position-diagnostics.v1.ini`, covering diagnostics, exact-reference uncertainty, duplicate Start, the six-page workspace, bilingual controls and prior RF clock behavior.
- 9 portable-package checks passed with a clean checkout path containing Thai text/spaces and no Python on launch PATH. Integrity, repeated installation, repair without replacing damaged originals, and invalid payload rejection were exercised.
- The packaged app opened six pages without automatic BLE acquisition or RTLS traffic.
- English/Thai diagnostic screens were rendered and inspected using an isolated UI fixture. Fixture screenshots are not live RF position evidence.
- The 2.1.1 user session was replayed read-only. The initial replay reproduced 40 solver attempts and zero accepted positions: 23 poorly conditioned, 13 exceeding uncertainty, and 4 ambiguous.
- A later user-confirmed equal-distance reference at (0,0,1.5) m produced 13 complete groups, all exceeding uncertainty. Median measured range differences to A1 were 0.582/1.253/1.243 m for A2/A3/A4, versus expected zero under the entered anchor geometry. A4 flagged NLOS in 13/13 groups.
- The current 0.30 m pairwise noise model predicts Z95 approximately 1.247 m at this reference even with ideal clocks and LOS, above the configured 1 m acceptance maximum.

Release payload: `deployment/windows-x64/2.1.2/UWB_Board_Programmer_2_1_2_Windows_x64.zip`

- Bytes: 95,431,663
- SHA-256: `bd73fd774fdc30f44dc8f2c07852483c216e55c9ad092d1d01ca7b391069cbe5`
- Files: 560
- Firmware unchanged: 1.3.4-pilot
- Previous files/releases preserved; new revision paths only.

No successful real-RF 3D positioning accuracy or live RTLS publishing acceptance is claimed.
The changes retain the current algorithms and acceptance criteria, expose rejection diagnostics,
and prevent duplicate Start requests from resetting the RF model. Survey, timing bias, NLOS and clock errors
still need independent reference calibration/validation across positions and heights.
