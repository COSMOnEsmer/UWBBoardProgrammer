# UWB Board Programmer 2.8.1

Run `START_HERE_2_8_1.cmd` on Windows x64. Python and vendor SDK installation are not required. Existing releases and profiles are preserved. BLE hardware and compatible board firmware are required for live acquisition.

This revision compares RF SYNC gap and validation spans in the Master clock domain. A faster Slave clock no longer fails the exact 1.5-second boundary solely because of oscillator skew. Clock noise, freshness, minimum sample count, no-extrapolation and position quality gates are unchanged.

RTLS Platform now reports `Position ACK` and `Position errors` separately from aggregate heartbeat/device-status acknowledgements. Each acknowledged live position is recorded in the activity log. An active Tag or online gateway does not imply a fresh accepted coordinate. Experimental continuous estimates remain local and are not published as accepted RTLS positions.

Validation: 91 regression tests and 9 portable deployment checks passed. A timing-preserved replay increased solver opportunities (11 to 26 in the tested two-minute interval), with one accepted fix in both versions. This is not evidence of improved position accuracy or a higher accepted-fix rate.

During the real 2.8.0 hardware test on 4 November 2026, the RTLS history independently confirmed TP-T1 at (1.155, 0.181, 1.306) metres at 09:43:31 UTC. The physical reference was approximate (1.2, 0.5, 1.2) metres. Sparse accepted fixes and RF/geometry uncertainty remain under investigation; no synthetic or replay coordinates were published.

Coordinate registration and Auto Survey behavior are described in `docs/COORDINATE_ALIGNMENT_2_8_0.md`. The existing confirmed Floor profile is retained; no firmware changes or recalibration are required for this PC software update.
