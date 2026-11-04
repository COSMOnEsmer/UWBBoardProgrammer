# 2.5.0 display and panel validation

The existing hardware timing, solver acceptance and RTLS publishing paths are
unchanged. This update affects display persistence, five-second trajectory history
and panel layout. It does not generate positions during missing measurements.

46 software tests passed. New tests verify that repeated snapshots do not refresh
the original sample age; missing samples retain the last point; trajectory samples
older than five seconds expire; and live widget identity/signals survive panel
detach and close-to-reattach. Existing clock, calibration, rejection and preview
tests also passed. English/Thai and detached 2D/3D UI fixture renders were inspected.
Fixtures do not constitute a new real-board positioning or accuracy test.

Final portable package: 95,981,734 bytes, 579 files, SHA-256
`b80012fe38863a7ebfa8d845201a54584f632a9f0dcb006ce7ef5f0b2149fa4f`.
The final package uses launcher/manifest v10 and the 2.5.0-final archive directory.
Nine portable checks passed: verification, install/reuse, no-Python launch,
preserving/repairing a damaged disposable installation, and rejecting invalid
archives. Test checkout uses a short path containing Thai text and spaces.

The new Desktop shortcut is UWB Board Programmer 2.5.0. Launcher migration copies
append-only profiles/preferences, without replacing original files. It selects the
latest saved profile at launch. Earlier programs and RTLSSimulator remain preserved.
No profiles, credentials or measurement recordings are in the published archive.

Local receipts:

- `verification/pv10-042112858956/report.json`
- `verification/installation-2.5.0-20261104T042122190539Z.json`
- `verification/path-final-ui-041503/`

RTLS instructions were checked against the project's supplied Edge Integration
Guide and current CloudClient/GUI code. The dashboard could not be loaded through
the web inspection tool. No new server configuration or live publishing test was
performed. Accepted fresh fixes remain eligible for RTLS; experimental Warning
and stale held display positions do not enter that publishing path.
