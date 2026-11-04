# UWB Board Programmer 2.8.2

Run START_HERE_2_8_2.cmd on Windows x64. The previous releases remain available.

Continuous estimates are now published to RTLS when positioning is running, live position publishing is checked, and continuous estimates are enabled. Fresh, finite estimates from real RF measurements are sent even when the strict solver rejects ambiguity or uncertainty. Quality metadata marks them as estimated with a Warning. The platform may ignore optional quality fields; the desktop explicitly identifies this mode. An RTLS acknowledgement confirms ingestion, not accuracy.

Approximate positions select a solution continuous with the previous estimate among similarly fitting candidates. Accuracy is unverified: the transmitted accuracy_m is conservatively set to at least the workspace diagonal, not a measured confidence interval. This avoids claiming validated accuracy.

No stale coordinates are re-sent as fresh positions. The desktop retains the last marker with its age during a data gap; the external platform controls its own stale-marker lifetime. Pause positioning, disable publishing, or disable continuous estimates to stop approximate publishing. Accepted-fix processing remains available independently. Recordings distinguish estimated_position from fix.

This update changes PC software only. Firmware and confirmed Floor calibration are retained. No credentials or personal recordings are included in GitHub or the portable package.
