# UWB Board Programmer 2.1.1 — BLE loss and RF clock recovery

Run **START_HERE_2_1_1.cmd** or the **UWB Board Programmer 2.1.1** Desktop shortcut.
The original application/files are preserved. Board firmware remains **1.3.4-pilot**; this PC update does not require reflashing.

For a bench test, discover/assign A1–A4 and use **BLE/GATT → Connect BLE + record**.
Clock models accumulate without surveyed coordinates. These diagnostics assume zero propagation distance and report model stability only, not corrected absolute synchronization or position accuracy. No XYZ is computed and RTLS connection is blocked until the user confirms measured coordinates.

For real 3D positioning, disconnect, install non-coplanar anchors, measure their antenna X/Y/Z in metres, enter the survey and Tag bounds, and check **Anchor coordinates were measured at the physical antenna positions**. Save a new profile, then open **Live positioning → Connect BLE + record → Start positioning**.

BLE telemetry loss is recorded separately from a hardware clock-domain reset. Boot changes and disconnects still reset the RF epoch. Timestamp CRC/identity/freshness checks remain active. The BLE pipeline waits for RF SYNC timestamps bracketing each BLINK and uses bounded interpolation, never extrapolation. Brackets wider than 1.5 s are rejected. At least six samples, fresh SYNC, skew within 200 ppm and validation RMS below 2 ns are required. VALIDATION ns is recent skip-one SYNC interpolation error, rather than a long-window linear-regression residual. A later SYNC can add processing latency. Frames that wait too long or fail quality checks are rejected.

Survey confirmation is unchecked by default for old profiles. With trial coordinates or coplanar tabletop boards, leave it unchecked and use diagnostics. Verify actual 3D results against measured reference points before evaluating accuracy. USB legacy retains its original regression engine.

RTLS requires the measured survey to match server Site/Floor/anchor IDs/coordinates, plus a Gateway ID and token. Replay remains local. Credentials, measurements and board backups are excluded from distribution. Profiles/language settings are copied from an earlier local installation into the new one; old files remain untouched. Enter the token again in the new installation when ready to connect RTLS.
